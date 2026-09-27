"""Pantalla de reportes: ventas y utilidad, stock bajo, saldos y cierres de caja (cierre F5).

Decisión: para "guardar" el Excel exportado se usa una ruta fija bajo
`ctx.data_dir / "reportes"` (mismo patrón que `import_view._exportacion_path`), en vez de un
diálogo `FilePicker.save_file`: es más simple y consistente con el resto del repo, que no usa ese
diálogo en ninguna pantalla existente.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import flet as ft

from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.reportes.schemas import (
    AccountBalanceRow,
    CashClosureRow,
    LowStockRow,
    SalesProfitRow,
)
from sistemashn.comercial.reportes.service import ReportService
from sistemashn.comercial.ui.components import tiene_permiso
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO = "com.reportes.ver"

_REPORTES = (
    ("ventas_utilidad", "Ventas y utilidad"),
    ("stock_bajo", "Stock bajo"),
    ("cxc", "Saldos por cobrar"),
    ("cxp", "Saldos por pagar"),
    ("cierres_caja", "Cierres de caja"),
)


def _exportacion_path(ctx: AppContext, report_name: str) -> Path:
    base = ctx.data_dir or Path(".")
    nombre = f"{report_name}-{datetime.now():%Y%m%d-%H%M}.xlsx"
    return base / "reportes" / nombre


def build_reports_view(ctx: AppContext) -> ft.Control:
    if not tiene_permiso(ctx, PERMISO):
        return widgets.forbidden_view()

    reports: ReportService = ctx.service("reports")

    campo_reporte = ft.Dropdown(
        label="Reporte",
        value="ventas_utilidad",
        options=[ft.DropdownOption(key=v, text=t) for v, t in _REPORTES],
    )
    campo_desde = widgets.form_field("Desde (AAAA-MM-DD)")
    campo_hasta = widgets.form_field("Hasta (AAAA-MM-DD)")
    fechas_row = ft.Row(controls=[campo_desde, campo_hasta], spacing=theme.SPACING["sm"])

    error = ft.Text("", color=theme.ERROR)
    mensaje = ft.Text("", color=theme.SUCCESS)
    resultado_area = ft.Column(spacing=theme.SPACING["sm"])

    estado: dict = {"rows": None}

    def _requiere_fechas() -> bool:
        return campo_reporte.value in ("ventas_utilidad", "cierres_caja")

    def _parse_fecha(texto: str, etiqueta: str) -> datetime | None:
        texto = (texto or "").strip()
        if not texto:
            error.value = f"indique la fecha '{etiqueta}'"
            return None
        try:
            fecha = datetime.strptime(texto, "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            error.value = f"fecha '{etiqueta}' inválida, use AAAA-MM-DD"
            return None
        return fecha

    def _render_result() -> None:
        resultado_area.controls = []
        if resultado_area.page is not None:
            resultado_area.update()
        if error.page is not None:
            error.update()
        if mensaje.page is not None:
            mensaje.update()

    def _generar(_: ft.Event[ft.Control]) -> None:
        error.value = ""
        mensaje.value = ""
        estado["rows"] = None
        tipo = campo_reporte.value

        try:
            if tipo == "ventas_utilidad":
                desde = _parse_fecha(campo_desde.value or "", "desde")
                if desde is None:
                    _render_result()
                    return
                hasta = _parse_fecha(campo_hasta.value or "", "hasta")
                if hasta is None:
                    _render_result()
                    return
                reporte = reports.sales_and_profit(ctx.actor, desde, hasta)
                estado["rows"] = list(reporte.rows)
                resultado_area.controls = _tabla_ventas(reporte.rows, reporte)
            elif tipo == "stock_bajo":
                pagina = reports.low_stock(ctx.actor, page=1)
                estado["rows"] = list(pagina.items)
                resultado_area.controls = [_tabla_stock_bajo(pagina.items)]
            elif tipo == "cxc":
                filas = reports.account_balances(ctx.actor, AccountKind.RECEIVABLE.value)
                resultado_area.controls = [_tabla_saldos(filas)]
            elif tipo == "cxp":
                filas = reports.account_balances(ctx.actor, AccountKind.PAYABLE.value)
                resultado_area.controls = [_tabla_saldos(filas)]
            elif tipo == "cierres_caja":
                desde = _parse_fecha(campo_desde.value or "", "desde")
                if desde is None:
                    _render_result()
                    return
                hasta = _parse_fecha(campo_hasta.value or "", "hasta")
                if hasta is None:
                    _render_result()
                    return
                filas = reports.cash_closures(ctx.actor, desde, hasta)
                resultado_area.controls = [_tabla_cierres(filas)]
        except SistemasHNError as exc:
            error.value = str(exc)
            resultado_area.controls = []

        _render_result()

    def _exportar(_: ft.Event[ft.Control]) -> None:
        error.value = ""
        mensaje.value = ""
        filas = estado["rows"]
        tipo = campo_reporte.value
        if tipo not in ("ventas_utilidad", "stock_bajo"):
            error.value = "este reporte no se puede exportar a Excel"
            _render_result()
            return
        if not filas:
            error.value = "genere el reporte antes de exportarlo"
            _render_result()
            return
        try:
            destino = _exportacion_path(ctx, tipo)
            destino.parent.mkdir(parents=True, exist_ok=True)
            reports.export_excel(ctx.actor, tipo, filas, destino)
            mensaje.value = f"Reporte exportado a: {destino}"
        except SistemasHNError as exc:
            error.value = str(exc)
        _render_result()

    def _on_reporte_change(_: ft.Event[ft.Control]) -> None:
        resultado_area.controls = []
        error.value = ""
        mensaje.value = ""
        estado["rows"] = None
        root.controls = _build()
        if root.page is not None:
            root.update()

    campo_reporte.on_change = _on_reporte_change

    def _build() -> list[ft.Control]:
        controles: list[ft.Control] = [
            widgets.page_header("Reportes"),
            campo_reporte,
        ]
        if _requiere_fechas():
            controles.append(fechas_row)
        controles.extend(
            [
                ft.Row(
                    controls=[
                        widgets.primary_button("Generar", _generar),
                        widgets.secondary_button("Exportar a Excel", _exportar),
                    ],
                    spacing=theme.SPACING["sm"],
                ),
                error,
                mensaje,
                resultado_area,
            ]
        )
        return controles

    root = ft.Column(spacing=theme.SPACING["md"], expand=True, scroll=ft.ScrollMode.AUTO)
    root.controls = _build()
    return root


def _tabla_ventas(rows: tuple[SalesProfitRow, ...], reporte) -> list[ft.Control]:
    if not rows:
        return [widgets.empty_state("No hay ventas en el rango indicado.")]
    columnas = ["Número", "Fecha", "Total", "Costo", "Utilidad"]
    filas = [
        [
            ft.Text(r.number),
            ft.Text(r.sold_at.date().isoformat()),
            widgets.money_text(r.total),
            widgets.money_text(r.cost) if r.cost is not None else ft.Text("—"),
            widgets.money_text(r.profit) if r.profit is not None else ft.Text("—"),
        ]
        for r in rows
    ]
    tabla = ft.DataTable(
        columns=[ft.DataColumn(label=ft.Text(c)) for c in columnas],
        rows=[ft.DataRow(cells=[ft.DataCell(c) for c in fila]) for fila in filas],
    )
    utilidad_txt = (
        widgets.format_lempiras(reporte.total_profit) if reporte.total_profit is not None else "—"
    )
    resumen = ft.Text(
        f"Total: {widgets.format_lempiras(reporte.total_sales)} · Utilidad: {utilidad_txt}"
    )
    return [tabla, resumen]


def _tabla_stock_bajo(rows: list[LowStockRow]) -> ft.Control:
    if not rows:
        return widgets.empty_state("No hay productos bajo el mínimo.")
    columnas = ["Código", "Nombre", "Existencia", "Reservado", "Disponible", "Mínimo"]
    filas = [
        [
            ft.Text(r.code),
            ft.Text(r.name),
            ft.Text(str(r.on_hand)),
            ft.Text(str(r.reserved)),
            ft.Text(str(r.available)),
            ft.Text(str(r.min_stock)),
        ]
        for r in rows
    ]
    return ft.DataTable(
        columns=[ft.DataColumn(label=ft.Text(c)) for c in columnas],
        rows=[ft.DataRow(cells=[ft.DataCell(c) for c in fila]) for fila in filas],
    )


def _tabla_saldos(rows: list[AccountBalanceRow]) -> ft.Control:
    if not rows:
        return widgets.empty_state("No hay cuentas registradas.")
    columnas = ["Contraparte", "Saldo", "Vencimiento", "Estado"]
    filas = [
        [
            ft.Text(r.party_name),
            widgets.money_text(r.balance),
            ft.Text(r.due_date.isoformat()),
            ft.Text(r.status.capitalize()),
        ]
        for r in rows
    ]
    return ft.DataTable(
        columns=[ft.DataColumn(label=ft.Text(c)) for c in columnas],
        rows=[ft.DataRow(cells=[ft.DataCell(c) for c in fila]) for fila in filas],
    )


def _tabla_cierres(rows: list[CashClosureRow]) -> ft.Control:
    if not rows:
        return widgets.empty_state("No hay cierres de caja en el rango indicado.")
    columnas = ["Cierre", "Apertura", "Esperado", "Contado", "Diferencia"]
    filas = [
        [
            ft.Text(r.closed_at.isoformat()),
            widgets.money_text(r.opening_amount),
            widgets.money_text(r.expected_cash),
            widgets.money_text(r.counted_cash),
            widgets.money_text(r.difference),
        ]
        for r in rows
    ]
    return ft.DataTable(
        columns=[ft.DataColumn(label=ft.Text(c)) for c in columnas],
        rows=[ft.DataRow(cells=[ft.DataCell(c) for c in fila]) for fila in filas],
    )
