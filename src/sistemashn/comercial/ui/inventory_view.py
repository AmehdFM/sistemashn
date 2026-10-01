"""Pantalla de inventario: búsqueda de producto, existencias, movimientos y ajuste (T2.6a)."""

from __future__ import annotations

import flet as ft

from sistemashn.comercial.catalogo.schemas import ProductView
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.ui.components import adjust_button, stock_and_movements_section
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_inventory_view(ctx: AppContext) -> ft.Control:
    catalog: CatalogService = ctx.service("catalog")

    campo_busqueda = widgets.form_field("Buscar producto por código, nombre o código de barras")
    estado: dict[str, object] = {"producto": None, "mov_page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar() -> None:
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _cambiar_pagina_movimientos(pagina: int) -> None:
        estado["mov_page"] = pagina
        _recargar()

    def _buscar(_: ft.Event[ft.Control]) -> None:
        texto = (campo_busqueda.value or "").strip()
        estado["mov_page"] = 1
        if not texto:
            estado["producto"] = None
            _recargar()
            return
        try:
            encontrado = catalog.find_by_code_or_barcode(ctx.actor, texto)
        except SistemasHNError as exc:
            estado["producto"] = None
            estado["error"] = str(exc)
            _recargar()
            return
        estado["error"] = None
        estado["producto"] = encontrado
        _recargar()

    campo_busqueda.on_submit = _buscar

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Inventario")
        filtros = ft.Row(
            controls=[campo_busqueda, widgets.primary_button("Buscar", _buscar)],
            spacing=theme.SPACING["sm"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        controles: list[ft.Control] = [encabezado, filtros]

        error = estado.get("error")
        if error:
            controles.append(widgets.error_banner(str(error)))
            return controles

        producto: ProductView | None = estado.get("producto")  # type: ignore[assignment]
        if producto is None:
            controles.append(widgets.empty_state("Busque un producto para ver su inventario."))
            return controles

        controles.append(
            ft.Text(
                f"{producto.code} · {producto.name}",
                size=theme.FONT_SUBTITLE,
                weight=ft.FontWeight.W_600,
            )
        )
        controles.append(
            stock_and_movements_section(
                ctx, producto.id, int(estado["mov_page"]), _cambiar_pagina_movimientos
            )
        )
        boton_ajuste = adjust_button(ctx, producto.id, _recargar)
        if boton_ajuste is not None:
            controles.append(boton_ajuste)
        return controles

    root.controls = _render()
    return root
