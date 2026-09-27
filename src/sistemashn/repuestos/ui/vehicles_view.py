"""Pantalla `/repuestos/vehiculos`: marcas y modelos de vehículo (T2.6b)."""

from __future__ import annotations

import flet as ft

from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_PERMISO_GESTIONAR = "rep.vehiculos.gestionar"


def _abrir_dialogo(dialog: ft.AlertDialog, control: ft.Control) -> None:
    if control.page is not None:
        control.page.show_dialog(dialog)


def build_vehicles_view(ctx: AppContext) -> ft.Control:
    vehicles = ctx.service("vehicles")

    with session_scope(ctx.session_factory, readonly=True) as session:
        puede_gestionar = ctx.authorizer.can(session, ctx.actor, _PERMISO_GESTIONAR)

    estado = {"make_id": None}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar() -> None:
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _dialogo_nueva_marca(control: ft.Control) -> None:
        campo_nombre = widgets.form_field("Nombre de la marca", autofocus=True)
        error = ft.Text("", color=theme.ERROR)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva marca"),
            content=ft.Column(controls=[campo_nombre, error], tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                nuevo_id = vehicles.create_make(ctx.actor, campo_nombre.value or "")
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            estado["make_id"] = nuevo_id
            _recargar()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Crear", _guardar),
        ]
        _abrir_dialogo(dialog, control)

    def _dialogo_nuevo_modelo(control: ft.Control) -> None:
        if estado["make_id"] is None:
            return
        campo_nombre = widgets.form_field("Nombre del modelo", autofocus=True)
        error = ft.Text("", color=theme.ERROR)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo modelo"),
            content=ft.Column(controls=[campo_nombre, error], tight=True),
        )

        def _cancelar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _guardar(_: ft.Event[ft.Control]) -> None:
            try:
                vehicles.create_model(ctx.actor, estado["make_id"], campo_nombre.value or "")
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            dialog.open = False
            dialog.update()
            _recargar()

        dialog.actions = [
            widgets.secondary_button("Cancelar", _cancelar),
            widgets.primary_button("Crear", _guardar),
        ]
        _abrir_dialogo(dialog, control)

    def _seleccionar_marca(make_id: int) -> None:
        estado["make_id"] = make_id
        _recargar()

    def _render_marcas() -> ft.Control:
        acciones = []
        if puede_gestionar:
            acciones.append(
                widgets.primary_button("Nueva marca", lambda e: _dialogo_nueva_marca(e.control))
            )
        try:
            marcas = vehicles.list_makes(ctx.actor)
        except SistemasHNError as exc:
            return ft.Column(controls=[widgets.error_banner(str(exc))])

        if not marcas:
            return ft.Column(
                controls=[
                    ft.Row(controls=acciones, alignment=ft.MainAxisAlignment.END),
                    widgets.empty_state("No hay marcas registradas."),
                ]
            )

        filas = [
            ft.ListTile(
                title=ft.Text(marca.name),
                selected=marca.id == estado["make_id"],
                on_click=lambda e, m=marca: _seleccionar_marca(m.id),
            )
            for marca in marcas
        ]
        return ft.Column(
            controls=[
                ft.Row(controls=acciones, alignment=ft.MainAxisAlignment.END),
                ft.Column(controls=filas, spacing=0),
            ],
            spacing=theme.SPACING["sm"],
        )

    def _render_modelos() -> ft.Control:
        if estado["make_id"] is None:
            return widgets.empty_state("Seleccione una marca para ver sus modelos.")

        acciones = []
        if puede_gestionar:
            acciones.append(
                widgets.primary_button("Nuevo modelo", lambda e: _dialogo_nuevo_modelo(e.control))
            )
        try:
            modelos = vehicles.list_models(ctx.actor, estado["make_id"])
        except SistemasHNError as exc:
            return ft.Column(controls=[widgets.error_banner(str(exc))])

        if not modelos:
            return ft.Column(
                controls=[
                    ft.Row(controls=acciones, alignment=ft.MainAxisAlignment.END),
                    widgets.empty_state("Esta marca no tiene modelos registrados."),
                ]
            )

        filas = [ft.ListTile(title=ft.Text(modelo.name)) for modelo in modelos]
        return ft.Column(
            controls=[
                ft.Row(controls=acciones, alignment=ft.MainAxisAlignment.END),
                ft.Column(controls=filas, spacing=0),
            ],
            spacing=theme.SPACING["sm"],
        )

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Vehículos")
        cuerpo = ft.Row(
            controls=[
                ft.Container(content=_render_marcas(), expand=1),
                ft.VerticalDivider(),
                ft.Container(content=_render_modelos(), expand=1),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True,
        )
        return [encabezado, cuerpo]

    root.controls = _render()
    return root
