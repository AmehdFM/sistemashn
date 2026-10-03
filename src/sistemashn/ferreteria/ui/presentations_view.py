"""Consulta de atributos y presentaciones, sin libro de inventario paralelo."""

from __future__ import annotations

import flet as ft

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_presentations_view(ctx: AppContext) -> ft.Control:
    catalog = ctx.service("catalog")
    fer_catalog = ctx.service("fer_catalog")
    query = widgets.form_field("Buscar artículo")
    query.hint_text = "SKU, nombre o código de barras"
    results = ft.Column(spacing=theme.SPACING["sm"])
    notice = ft.Text("", color=theme.ERROR)

    def _show_product(product: object) -> None:
        try:
            item = fer_catalog.get_item(ctx.actor, product.id)
            packs = fer_catalog.list_packs(ctx.actor, product.id)
        except SistemasHNError as exc:
            notice.value = str(exc)
            if notice.page is not None:
                notice.update()
            return

        parts = [getattr(item, field, None) for field in ("brand", "family", "specs")]
        description = " · ".join(str(part) for part in parts if part)
        cells: list[ft.Control] = [
            ft.Text(
                f"{product.code} · {product.name}",
                size=theme.FONT_SUBTITLE,
                weight=ft.FontWeight.W_600,
            ),
            ft.Text(description or "Sin datos técnicos adicionales.", color=theme.TEXT_MUTED),
        ]
        if packs:
            cells.extend(
                ft.Row(
                    controls=[
                        ft.Text(pack.label, expand=True),
                        ft.Text(f"× {pack.factor_base} unidad base"),
                        ft.Text(pack.code or "Sin código", color=theme.TEXT_MUTED),
                    ],
                    wrap=True,
                    spacing=theme.SPACING["md"],
                )
                for pack in packs
                if pack.active
            )
        else:
            cells.append(ft.Text("Sin empaques adicionales.", color=theme.TEXT_MUTED))
        results.controls = [ft.Column(controls=cells, spacing=theme.SPACING["sm"])]
        if results.page is not None:
            results.update()

    def _search(_: ft.Event[ft.Control]) -> None:
        text = (query.value or "").strip()
        if not text:
            notice.value = "Escriba un SKU, nombre o código de barras."
            if notice.page is not None:
                notice.update()
            return
        try:
            exact = catalog.find_by_code_or_barcode(ctx.actor, text)
            page = catalog.search(ctx.actor, text, page=1, page_size=20)
        except SistemasHNError as exc:
            notice.value = str(exc)
            if notice.page is not None:
                notice.update()
            return
        notice.value = ""
        products = list(page.items)
        if exact is not None and all(product.id != exact.id for product in products):
            products.insert(0, exact)
        results.controls = (
            [
                ft.ListTile(
                    title=ft.Text(f"{product.code} · {product.name}"),
                    subtitle=ft.Text(str(product.barcode or "")),
                    trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                    on_click=lambda e, selected=product: _show_product(selected),
                )
                for product in products
            ]
            if products
            else [widgets.empty_state("No se encontraron artículos.")]
        )
        if notice.page is not None:
            notice.update()
            results.update()

    query.on_submit = _search
    return ft.Column(
        controls=[
            widgets.page_header(
                "Medidas y empaques",
                "Consulte la identidad técnica y la equivalencia de cada presentación.",
            ),
            ft.Row(
                controls=[query, widgets.primary_button("Buscar", _search, icon=ft.Icons.SEARCH)],
                wrap=True,
                spacing=theme.SPACING["sm"],
            ),
            notice,
            results,
        ],
        spacing=theme.SPACING["md"],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
