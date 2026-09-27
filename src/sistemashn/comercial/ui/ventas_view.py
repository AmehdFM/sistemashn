"""Pantalla de ventas: historial de solo lectura (T4.6)."""

from __future__ import annotations

import flet as ft

from sistemashn.comercial.ui.components import safe_page
from sistemashn.comercial.ventas.schemas import SaleSummary, SaleView
from sistemashn.comercial.ventas.service import SaleService
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_sales_view(ctx: AppContext) -> ft.Control:
    sales: SaleService = ctx.service("sales")

    campo_busqueda = widgets.form_field("Buscar por número")
    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    campo_busqueda.on_submit = lambda _: _recargar(1)

    def _ver(control: ft.Control, resumen: SaleSummary) -> None:
        try:
            venta = sales.get(ctx.actor, resumen.id)
        except SistemasHNError as exc:
            dialog_err = ft.AlertDialog(
                modal=True, title=ft.Text("Error"), content=widgets.error_banner(str(exc))
            )
            pagina = safe_page(control)
            if pagina is not None:
                pagina.show_dialog(dialog_err)
            return
        _mostrar_detalle(control, venta)

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Ventas")
        filtros = ft.Row(controls=[campo_busqueda], spacing=theme.SPACING["md"])

        try:
            pagina = sales.list(ctx.actor, text=campo_busqueda.value or "", page=estado["page"])
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay ventas registradas.")]

        columnas = ["Número", "Cliente", "Fecha", "Total", "Estado", ""]
        filas: list[list[ft.Control]] = []
        for resumen in pagina.items:
            filas.append(
                [
                    ft.Text(resumen.number),
                    ft.Text(str(resumen.customer_id) if resumen.customer_id else "—"),
                    ft.Text(resumen.sold_at.date().isoformat()),
                    widgets.money_text(resumen.total),
                    ft.Text(resumen.status.capitalize()),
                    widgets.secondary_button("Ver", lambda e, r=resumen: _ver(e.control, r)),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    root.controls = _render()
    return root


def _mostrar_detalle(control: ft.Control, venta: SaleView) -> None:
    lineas: list[ft.Control] = [ft.Text("Líneas", weight=ft.FontWeight.BOLD)]
    for linea in venta.lines:
        if linea.kit_component_of is not None:
            # Línea de componente de un kit: se muestra indentada con un prefijo distintivo.
            lineas.append(
                ft.Text(
                    f"    · componente: {linea.description_snapshot} · cant {linea.qty}",
                    color=theme.TEXT_MUTED,
                )
            )
        else:
            lineas.append(
                ft.Text(
                    f"{linea.description_snapshot} · cant {linea.qty} · "
                    f"precio {widgets.format_lempiras(linea.unit_price)} · "
                    f"total {widgets.format_lempiras(linea.line_total)}"
                )
            )

    pagos: list[ft.Control] = [ft.Text("Pagos", weight=ft.FontWeight.BOLD)]
    if venta.payments:
        for pago in venta.payments:
            pagos.append(
                ft.Text(
                    f"{pago.method} · {widgets.format_lempiras(pago.amount)}"
                    + (f" · ref: {pago.reference}" if pago.reference else "")
                )
            )
    else:
        pagos.append(ft.Text("Sin pagos registrados."))

    resumen: list[ft.Control] = [
        ft.Text(f"Subtotal: {widgets.format_lempiras(venta.subtotal)}"),
        ft.Text(f"Impuesto: {widgets.format_lempiras(venta.tax_total)}"),
        ft.Text(f"Total: {widgets.format_lempiras(venta.total)}", weight=ft.FontWeight.BOLD),
        ft.Text(f"Pagado: {widgets.format_lempiras(venta.paid_amount)}"),
    ]
    if venta.change_amount > 0:
        resumen.append(ft.Text(f"Vuelto: {widgets.format_lempiras(venta.change_amount)}"))
    if venta.credit_amount > 0:
        resumen.append(ft.Text(f"Crédito: {widgets.format_lempiras(venta.credit_amount)}"))

    body = ft.Column(
        controls=[
            ft.Text(f"Venta {venta.number}", size=18, weight=ft.FontWeight.BOLD),
            *resumen,
            ft.Divider(),
            *lineas,
            ft.Divider(),
            *pagos,
        ],
        tight=True,
        scroll=ft.ScrollMode.AUTO,
        height=500,
        width=520,
    )

    dialog = ft.AlertDialog(modal=True, title=ft.Text("Detalle de venta"), content=body)

    def _cerrar(_: ft.Event[ft.Control]) -> None:
        dialog.open = False
        dialog.update()

    dialog.actions = [widgets.secondary_button("Cerrar", _cerrar)]
    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)
