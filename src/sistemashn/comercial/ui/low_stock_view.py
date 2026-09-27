"""Pantalla de stock bajo: productos cuyo disponible llegó al mínimo o menos (T2.6a)."""

from __future__ import annotations

import flet as ft

from sistemashn.comercial.inventario.service import InventoryService
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_low_stock_view(ctx: AppContext) -> ft.Control:
    inventory: InventoryService = ctx.service("inventory")

    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Stock bajo")

        try:
            pagina = inventory.low_stock(ctx.actor, estado["page"])
        except SistemasHNError as exc:
            return [encabezado, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [
                encabezado,
                widgets.empty_state("No hay productos con stock bajo.", icon=ft.Icons.CHECK_CIRCLE),
            ]

        columnas = ["Código", "Nombre", "Disponible", "Mínimo"]
        filas = [
            [
                ft.Text(item.code),
                ft.Text(item.name),
                ft.Text(str(item.available)),
                ft.Text(str(item.min_stock)),
            ]
            for item in pagina.items
        ]
        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, tabla]

    root.controls = _render()
    return root
