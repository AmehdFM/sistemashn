"""Diálogos de unidades y categorías, embebidos en la pantalla de catálogo (T2.6a)."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from sistemashn.comercial.catalogo.schemas import CategoryInput, CategoryView, UnitInput, UnitView
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.ui.components import safe_page, tiene_permiso
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_GESTIONAR = "com.catalogo.gestionar"


def _cerrar(dialog: ft.AlertDialog) -> None:
    dialog.open = False
    dialog.update()


def open_units_dialog(ctx: AppContext, control: ft.Control, on_changed: Callable[[], None]) -> None:
    """Diálogo de unidades: lista con alta/edición en línea."""
    catalog: CatalogService = ctx.service("catalog")
    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    body = ft.Column(spacing=theme.SPACING["sm"], tight=True, scroll=ft.ScrollMode.AUTO, height=400)
    dialog = ft.AlertDialog(modal=True, title=ft.Text("Unidades"), content=body)

    def _render() -> None:
        try:
            unidades = catalog.list_units(ctx.actor, include_inactive=True)
        except SistemasHNError as exc:
            body.controls = [widgets.error_banner(str(exc))]
            return

        filas: list[ft.Control] = []
        for unidad in unidades:
            filas.append(_fila_unidad(unidad))
        campos_nuevo = _form_unidad(None) if puede_gestionar else None
        body.controls = [*filas]
        if campos_nuevo is not None:
            body.controls.append(campos_nuevo)
        if not unidades:
            body.controls.insert(0, widgets.empty_state("No hay unidades registradas."))

    def _fila_unidad(unidad: UnitView) -> ft.Control:
        if not puede_gestionar:
            return ft.Text(f"{unidad.code} · {unidad.name}")
        return _form_unidad(unidad)

    def _form_unidad(unidad: UnitView | None) -> ft.Control:
        campo_codigo = widgets.form_field("Código", value=unidad.code if unidad else "")
        campo_nombre = widgets.form_field("Nombre", value=unidad.name if unidad else "")
        campo_fraccion = ft.Checkbox(
            label="Admite fracciones", value=unidad.allows_fraction if unidad else False
        )
        error = ft.Text("", color=theme.ERROR)

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                data = UnitInput(
                    code=campo_codigo.value or "",
                    name=campo_nombre.value or "",
                    allows_fraction=bool(campo_fraccion.value),
                )
                if unidad is None:
                    catalog.create_unit(ctx.actor, data)
                else:
                    catalog.update_unit(ctx.actor, unidad.id, data)
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            except Exception as exc:  # errores de validación de Pydantic
                error.value = str(exc)
                error.update()
                return
            on_changed()
            _render()
            body.update()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            campo_codigo,
                            campo_nombre,
                            campo_fraccion,
                            widgets.primary_button(
                                "Crear" if unidad is None else "Guardar", _guardar
                            ),
                        ],
                        wrap=True,
                        spacing=theme.SPACING["sm"],
                    ),
                    error,
                ],
                spacing=theme.SPACING["xs"],
            ),
            border=ft.Border.all(1, theme.BORDER),
            border_radius=ft.BorderRadius.all(theme.RADIUS),
            padding=ft.Padding.all(theme.SPACING["sm"]),
        )

    dialog.actions = [widgets.secondary_button("Cerrar", lambda e: _cerrar(dialog))]
    _render()
    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)


def open_categories_dialog(
    ctx: AppContext, control: ft.Control, on_changed: Callable[[], None]
) -> None:
    """Diálogo de categorías: lista con alta/edición en línea."""
    catalog: CatalogService = ctx.service("catalog")
    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    body = ft.Column(spacing=theme.SPACING["sm"], tight=True, scroll=ft.ScrollMode.AUTO, height=400)
    dialog = ft.AlertDialog(modal=True, title=ft.Text("Categorías"), content=body)

    def _render() -> None:
        try:
            categorias = catalog.list_categories(ctx.actor, include_inactive=True)
        except SistemasHNError as exc:
            body.controls = [widgets.error_banner(str(exc))]
            return

        filas = [_fila_categoria(c) for c in categorias]
        campo_nuevo = _form_categoria(None) if puede_gestionar else None
        body.controls = [*filas]
        if campo_nuevo is not None:
            body.controls.append(campo_nuevo)
        if not categorias:
            body.controls.insert(0, widgets.empty_state("No hay categorías registradas."))

    def _fila_categoria(categoria: CategoryView) -> ft.Control:
        if not puede_gestionar:
            return ft.Text(categoria.name)
        return _form_categoria(categoria)

    def _form_categoria(categoria: CategoryView | None) -> ft.Control:
        campo_nombre = widgets.form_field("Nombre", value=categoria.name if categoria else "")
        error = ft.Text("", color=theme.ERROR)

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                data = CategoryInput(name=campo_nombre.value or "")
                if categoria is None:
                    catalog.create_category(ctx.actor, data)
                else:
                    catalog.update_category(ctx.actor, categoria.id, data)
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            except Exception as exc:
                error.value = str(exc)
                error.update()
                return
            on_changed()
            _render()
            body.update()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            campo_nombre,
                            widgets.primary_button(
                                "Crear" if categoria is None else "Guardar", _guardar
                            ),
                        ],
                        wrap=True,
                        spacing=theme.SPACING["sm"],
                    ),
                    error,
                ],
                spacing=theme.SPACING["xs"],
            ),
            border=ft.Border.all(1, theme.BORDER),
            border_radius=ft.BorderRadius.all(theme.RADIUS),
            padding=ft.Padding.all(theme.SPACING["sm"]),
        )

    dialog.actions = [widgets.secondary_button("Cerrar", lambda e: _cerrar(dialog))]
    _render()
    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)
