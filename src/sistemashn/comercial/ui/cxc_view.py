"""Pantalla de cuentas por cobrar (CxC): listado, filtros y abonos (T4.6).

Decisión: se duplica el patrón de `cxp_view.py` (en vez de factorizar un helper compartido) para
no arriesgar las pruebas ya existentes de CxP; la única diferencia de negocio es
`AccountKind.RECEIVABLE`, los permisos `com.cxc.ver`/`com.cxc.cobrar` y la columna "Cliente".
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import uuid4

import flet as ft

from sistemashn.comercial.credito.schemas import AccountKind, AccountStatus, AccountSummary
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ui.components import safe_page, tiene_permiso
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_COBRAR = "com.cxc.cobrar"
_ESTADOS = (
    ("", "Todas"),
    (AccountStatus.PENDIENTE.value, "Pendiente"),
    (AccountStatus.VENCIDA.value, "Vencida"),
    (AccountStatus.PAGADA.value, "Pagada"),
)
_COLOR_ESTADO = {
    AccountStatus.PENDIENTE: theme.TEXT,
    AccountStatus.VENCIDA: theme.ERROR,
    AccountStatus.PAGADA: theme.SUCCESS,
}


def build_receivables_view(ctx: AppContext) -> ft.Control:
    accounts: AccountService = ctx.service("accounts")
    puede_cobrar = tiene_permiso(ctx, PERMISO_COBRAR)

    campo_busqueda = widgets.form_field("Buscar por cliente")
    campo_estado = ft.Dropdown(
        label="Estado",
        value="",
        options=[ft.DropdownOption(key=v, text=t) for v, t in _ESTADOS],
    )

    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    campo_busqueda.on_submit = lambda _: _recargar(1)
    campo_estado.on_change = lambda _: _recargar(1)

    def _acciones_fila(cuenta: AccountSummary) -> ft.Control:
        if not puede_cobrar or cuenta.status == AccountStatus.PAGADA:
            return ft.Text("—")
        return widgets.secondary_button(
            "Abonar", lambda e, c=cuenta: _open_pay_dialog(e.control, c)
        )

    def _open_pay_dialog(control: ft.Control, cuenta: AccountSummary) -> None:
        request_id = uuid4().hex
        campo_metodo = ft.Dropdown(
            label="Método de pago",
            value=PaymentMethod.EFECTIVO.value,
            options=[
                ft.DropdownOption(key=m.value, text=m.value.capitalize()) for m in PaymentMethod
            ],
        )
        campo_monto = widgets.form_field(
            f"Monto (saldo: {widgets.format_lempiras(cuenta.balance)})"
        )
        campo_referencia = widgets.form_field("Referencia (opcional)")
        error = ft.Text("", color=theme.ERROR)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Abonar a {cuenta.party_name}"),
            content=ft.Column(
                controls=[campo_metodo, campo_monto, campo_referencia, error], tight=True
            ),
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
            if monto <= 0 or monto > cuenta.balance:
                error.value = "el monto debe ser mayor a cero y no exceder el saldo"
                error.update()
                return
            try:
                pago = PaymentInput(
                    method=PaymentMethod(campo_metodo.value),
                    amount=monto,
                    reference=(campo_referencia.value or "").strip() or None,
                )
            except Exception as exc:  # validación de Pydantic
                error.value = str(exc)
                error.update()
                return
            try:
                accounts.pay(ctx.actor, cuenta.id, pago, request_id)
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

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Cuentas por cobrar")
        filtros = ft.Row(
            controls=[campo_busqueda, campo_estado],
            spacing=theme.SPACING["md"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        try:
            estado_filtro = AccountStatus(campo_estado.value) if campo_estado.value else None
            pagina = accounts.list(
                ctx.actor,
                AccountKind.RECEIVABLE,
                status=estado_filtro,
                text=campo_busqueda.value or "",
                page=estado["page"],
            )
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay cuentas por cobrar.")]

        columnas = ["Cliente", "Origen", "Monto original", "Saldo", "Vencimiento", "Estado", ""]
        filas: list[list[ft.Control]] = []
        for cuenta in pagina.items:
            filas.append(
                [
                    ft.Text(cuenta.party_name),
                    ft.Text(f"{cuenta.source_type} #{cuenta.source_id}"),
                    widgets.money_text(cuenta.original_amount),
                    widgets.money_text(cuenta.balance),
                    ft.Text(cuenta.due_date.isoformat()),
                    ft.Text(cuenta.status.value.capitalize(), color=_COLOR_ESTADO[cuenta.status]),
                    _acciones_fila(cuenta),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    root.controls = _render()
    return root
