"""Pantalla de caja: apertura/cierre de turno, movimientos e historial (T4.6)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import flet as ft

from sistemashn.comercial.caja.schemas import CashSessionView
from sistemashn.comercial.caja.service import CashService
from sistemashn.comercial.ui.components import safe_page, tiene_permiso
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_OPERAR = "com.caja.operar"
PERMISO_CERRAR = "com.caja.cerrar"


def build_cash_view(ctx: AppContext) -> ft.Control:
    cash: CashService = ctx.service("cash")
    puede_operar = tiene_permiso(ctx, PERMISO_OPERAR)
    puede_cerrar = tiene_permiso(ctx, PERMISO_CERRAR)

    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True, scroll=ft.ScrollMode.AUTO)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _abrir_dialogo_apertura(control: ft.Control) -> None:
        campo_monto = widgets.form_field("Monto de apertura")
        error = ft.Text("", color=theme.ERROR)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Abrir caja"),
            content=ft.Column(controls=[campo_monto, error], tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                monto = Decimal((campo_monto.value or "").strip().replace(",", ""))
            except InvalidOperation:
                error.value = "el monto es inválido"
                error.update()
                return
            try:
                cash.open(ctx.actor, monto)
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            _recargar()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Abrir", _guardar),
        ]
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    def _abrir_dialogo_movimiento(control: ft.Control, salida: bool) -> None:
        campo_monto = widgets.form_field("Monto")
        campo_motivo = widgets.form_field("Motivo (mínimo 5 caracteres)")
        error = ft.Text("", color=theme.ERROR)
        titulo = "Salida manual" if salida else "Entrada manual"
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(titulo),
            content=ft.Column(controls=[campo_monto, campo_motivo, error], tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                monto = Decimal((campo_monto.value or "").strip().replace(",", ""))
            except InvalidOperation:
                error.value = "el monto es inválido"
                error.update()
                return
            try:
                if salida:
                    cash.manual_exit(ctx.actor, monto, campo_motivo.value or "")
                else:
                    cash.manual_entry(ctx.actor, monto, campo_motivo.value or "")
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            _recargar()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Guardar", _guardar),
        ]
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    def _abrir_dialogo_cierre(control: ft.Control) -> None:
        campo_contado = widgets.form_field("Monto contado")
        error = ft.Text("", color=theme.ERROR)
        resultado = ft.Text("")
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cerrar caja"),
            content=ft.Column(controls=[campo_contado, error, resultado], tight=True),
        )

        def _cerrar_dialogo(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()
            _recargar()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                contado = Decimal((campo_contado.value or "").strip().replace(",", ""))
            except InvalidOperation:
                error.value = "el monto es inválido"
                error.update()
                return
            try:
                sesion = cash.close(ctx.actor, contado)
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            error.value = ""
            resultado.value = (
                f"Esperado: {widgets.format_lempiras(sesion.expected_cash or Decimal('0'))} · "
                f"Contado: {widgets.format_lempiras(sesion.counted_cash or Decimal('0'))} · "
                f"Diferencia: {widgets.format_lempiras(sesion.difference or Decimal('0'))}"
            )
            dialog.content.update()
            dialog.actions = [widgets.primary_button("Cerrar", _cerrar_dialogo)]
            dialog.update()

        dialog.actions = [
            widgets.secondary_button("Cancelar", lambda e: _cerrar_dialogo(e)),
            widgets.primary_button("Cerrar caja", _guardar),
        ]
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    def _seccion_estado_actual() -> list[ft.Control]:
        try:
            sesion = cash.current(ctx.actor)
        except SistemasHNError as exc:
            return [widgets.error_banner(str(exc))]

        if sesion is None:
            controles: list[ft.Control] = [widgets.empty_state("No hay caja abierta.")]
            if puede_operar:
                controles.append(
                    widgets.primary_button(
                        "Abrir caja", lambda e: _abrir_dialogo_apertura(e.control)
                    )
                )
            return controles

        controles = [
            ft.Text("Sesión abierta", weight=ft.FontWeight.BOLD),
            ft.Text(f"Apertura: {widgets.format_lempiras(sesion.opening_amount)}"),
            ft.Text(f"Hora de apertura: {sesion.opened_at.isoformat()}"),
        ]
        botones: list[ft.Control] = []
        if puede_operar:
            botones.append(
                widgets.secondary_button(
                    "Entrada manual", lambda e: _abrir_dialogo_movimiento(e.control, False)
                )
            )
            botones.append(
                widgets.secondary_button(
                    "Salida manual", lambda e: _abrir_dialogo_movimiento(e.control, True)
                )
            )
        if puede_cerrar:
            botones.append(
                widgets.primary_button("Cerrar caja", lambda e: _abrir_dialogo_cierre(e.control))
            )
        if botones:
            controles.append(ft.Row(controls=botones, spacing=theme.SPACING["sm"], wrap=True))

        try:
            movimientos = cash.movements(ctx.actor, sesion.id, page=1, page_size=10)
        except SistemasHNError as exc:
            controles.append(widgets.error_banner(str(exc)))
            return controles

        controles.append(ft.Text("Movimientos recientes", weight=ft.FontWeight.BOLD))
        if movimientos.items:
            for movimiento in movimientos.items:
                controles.append(
                    ft.Text(
                        f"{movimiento.kind} · {widgets.format_lempiras(movimiento.amount)}"
                        + (f" · {movimiento.reason}" if movimiento.reason else "")
                    )
                )
        else:
            controles.append(widgets.empty_state("Sin movimientos registrados."))
        return controles

    def _seccion_historial() -> list[ft.Control]:
        try:
            pagina = cash.list_sessions(ctx.actor, page=estado["page"])
        except SistemasHNError as exc:
            return [widgets.error_banner(str(exc))]

        if not pagina.items:
            return [widgets.empty_state("Sin sesiones anteriores.")]

        columnas = ["Apertura", "Cierre", "Monto apertura", "Contado", "Diferencia", "Estado"]
        filas: list[list[ft.Control]] = []
        for sesion in pagina.items:
            filas.append(_fila_sesion(sesion, columnas))
        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [tabla]

    def _fila_sesion(sesion: CashSessionView, _columnas: list[str]) -> list[ft.Control]:
        return [
            ft.Text(sesion.opened_at.isoformat()),
            ft.Text(sesion.closed_at.isoformat() if sesion.closed_at else "—"),
            widgets.money_text(sesion.opening_amount),
            ft.Text(
                widgets.format_lempiras(sesion.counted_cash)
                if sesion.counted_cash is not None
                else "—"
            ),
            ft.Text(
                widgets.format_lempiras(sesion.difference) if sesion.difference is not None else "—"
            ),
            ft.Text(sesion.status.capitalize()),
        ]

    def _render() -> list[ft.Control]:
        return [
            widgets.page_header("Caja"),
            *_seccion_estado_actual(),
            ft.Divider(),
            ft.Text("Historial de sesiones", weight=ft.FontWeight.BOLD),
            *_seccion_historial(),
        ]

    root.controls = _render()
    return root
