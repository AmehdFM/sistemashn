"""Pantalla `/repuestos/compatibles`: productos compatibles por marca, modelo y año (T2.6b)."""

from __future__ import annotations

import flet as ft

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_compatible_view(ctx: AppContext) -> ft.Control:
    vehicles = ctx.service("vehicles")
    parts = ctx.service("parts")

    estado = {"make_id": None, "model_id": None, "year": None, "page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    campo_marca = ft.Dropdown(label="Marca", options=[])
    campo_modelo = ft.Dropdown(label="Modelo", options=[])
    campo_anio = widgets.form_field("Año")
    resultados = ft.Column(spacing=theme.SPACING["sm"])

    def _cargar_marcas() -> None:
        try:
            marcas = vehicles.list_makes(ctx.actor)
        except SistemasHNError:
            marcas = []
        campo_marca.options = [ft.DropdownOption(key=str(m.id), text=m.name) for m in marcas]

    def _cargar_modelos(make_id: int | None) -> None:
        if make_id is None:
            campo_modelo.options = []
            return
        try:
            modelos = vehicles.list_models(ctx.actor, make_id)
        except SistemasHNError:
            modelos = []
        campo_modelo.options = [ft.DropdownOption(key=str(m.id), text=m.name) for m in modelos]

    def _cambiar_marca(_: ft.Event[ft.Dropdown]) -> None:
        estado["make_id"] = int(campo_marca.value) if campo_marca.value else None
        estado["model_id"] = None
        campo_modelo.value = None
        _cargar_modelos(estado["make_id"])
        if campo_modelo.page is not None:
            campo_modelo.update()

    def _cambiar_modelo(_: ft.Event[ft.Dropdown]) -> None:
        estado["model_id"] = int(campo_modelo.value) if campo_modelo.value else None

    def _buscar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        try:
            anio = int(campo_anio.value or "")
        except ValueError:
            estado["year"] = None
        else:
            estado["year"] = anio
        resultados.controls = _render_resultados()
        if resultados.page is not None:
            resultados.update()

    def _render_resultados() -> list[ft.Control]:
        if estado["model_id"] is None or estado["year"] is None:
            return [widgets.empty_state("Elija marca, modelo y año, luego busque.")]

        try:
            pagina = parts.compatible_products(
                ctx.actor, estado["model_id"], estado["year"], page=estado["page"]
            )
        except SistemasHNError as exc:
            return [widgets.error_banner(str(exc))]

        if not pagina.items:
            return [widgets.empty_state("No hay productos compatibles.")]

        filas = [[ft.Text(p.code), ft.Text(p.name)] for p in pagina.items]
        return [widgets.paginated_table(["Código", "Nombre"], filas, pagina, _buscar)]

    _cargar_marcas()
    campo_marca.on_change = _cambiar_marca
    campo_modelo.on_change = _cambiar_modelo
    resultados.controls = _render_resultados()

    filtros = ft.Row(
        controls=[
            campo_marca,
            campo_modelo,
            campo_anio,
            widgets.primary_button("Buscar", lambda e: _buscar(1)),
        ],
        spacing=theme.SPACING["sm"],
    )

    root.controls = [widgets.page_header("Buscar por vehículo"), filtros, resultados]
    return root
