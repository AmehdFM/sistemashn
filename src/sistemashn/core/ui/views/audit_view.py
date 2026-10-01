"""Pantalla de auditoría: filtros, tabla paginada y detalle de cada evento (T1.6b-2)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import flet as ft

from sistemashn.core.audit.service import AuditEventView, AuditQuery
from sistemashn.core.errors import SistemasHNError, ValidationError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.views import format_local_datetime

_FORMATO_FECHA = "%Y-%m-%d"


def _parse_fecha(texto: str, *, fin_del_dia: bool) -> datetime | None:
    """Valida y convierte `AAAA-MM-DD`; `fin_del_dia` incluye hasta las 23:59:59.999999."""
    texto = texto.strip()
    if not texto:
        return None
    try:
        fecha = datetime.strptime(texto, _FORMATO_FECHA).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValidationError(f"fecha inválida (use AAAA-MM-DD): {texto!r}") from exc
    if fin_del_dia:
        fecha += timedelta(days=1, microseconds=-1)
    return fecha


def build_audit_view(ctx: AppContext) -> ft.Control:
    audit_service = ctx.service("audit")

    campo_accion = widgets.form_field("Acción (prefijo)")
    campo_usuario = widgets.form_field("ID de usuario")
    campo_desde = widgets.form_field("Desde (AAAA-MM-DD)")
    campo_hasta = widgets.form_field("Hasta (AAAA-MM-DD)")

    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _dialogo_detalle(evento: AuditEventView, control: ft.Control) -> None:
        texto = (
            json.dumps(evento.detail, indent=2, ensure_ascii=False, sort_keys=True)
            if evento.detail
            else "Sin detalle."
        )
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(evento.action),
            content=ft.Container(
                content=ft.Column(
                    controls=[ft.Text(texto, size=theme.FONT_BODY, selectable=True)],
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=480,
                height=360,
            ),
        )

        def _cerrar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        dialog.actions = [widgets.secondary_button("Cerrar", _cerrar)]
        if control.page is not None:
            control.page.show_dialog(dialog)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _filtrar(_: ft.Event[ft.Control]) -> None:
        _recargar(1)

    filtros = ft.Row(
        controls=[
            campo_accion,
            campo_usuario,
            campo_desde,
            campo_hasta,
            widgets.primary_button("Filtrar", _filtrar),
        ],
        wrap=True,
        spacing=theme.SPACING["sm"],
    )

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Auditoría")

        try:
            texto_usuario = (campo_usuario.value or "").strip()
            user_id = int(texto_usuario) if texto_usuario else None
            desde = _parse_fecha(campo_desde.value or "", fin_del_dia=False)
            hasta = _parse_fecha(campo_hasta.value or "", fin_del_dia=True)
        except (ValueError, ValidationError) as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        query = AuditQuery(
            since=desde,
            until=hasta,
            user_id=user_id,
            action_prefix=(campo_accion.value or "").strip() or None,
        )
        try:
            pagina = audit_service.list(ctx.actor, query, estado["page"])
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay eventos de auditoría.")]

        columnas = ["Fecha", "Usuario", "Acción", "Entidad", "Resumen", "Detalle"]
        filas: list[list[ft.Control]] = []
        for evento in pagina.items:
            filas.append(
                [
                    ft.Text(format_local_datetime(evento.occurred_at)),
                    ft.Text(evento.username),
                    ft.Text(evento.action),
                    ft.Text(evento.entity_type or "—"),
                    ft.Text(evento.summary),
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        tooltip="Ver detalle",
                        on_click=lambda e, ev=evento: _dialogo_detalle(ev, e.control),
                    ),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    root.controls = _render()
    return root
