"""Extensión de formulario de producto: datos de parte, equivalencias y compatibilidad (T2.6b).

Implementa `sistemashn.comercial.ui.extensions.ProductFormExtension`.
"""

from __future__ import annotations

import flet as ft

from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

_PERMISO_VER = "com.catalogo.ver"
_PERMISO_GESTIONAR = "rep.partes.gestionar"

_ORIGENES = (("original", "Original"), ("generico", "Genérico"))
_ANIO_MINIMO = 1950
_ANIO_MAXIMO = 2100


def _abrir_dialogo(dialog: ft.AlertDialog, control: ft.Control) -> None:
    if control.page is not None:
        control.page.show_dialog(dialog)


class PartFormExtension:
    """Sección "Datos de repuesto" del formulario de producto de Comercial."""

    title = "Datos de repuesto"

    def is_visible(self, ctx: AppContext) -> bool:
        if ctx.actor is None:
            return False
        with session_scope(ctx.session_factory, readonly=True) as session:
            return ctx.authorizer.can(session, ctx.actor, _PERMISO_VER)

    def build(self, ctx: AppContext, product_id: int) -> ft.Control:
        parts = ctx.service("parts")
        vehicles = ctx.service("vehicles")
        catalog = ctx.service("catalog")

        with session_scope(ctx.session_factory, readonly=True) as session:
            puede_gestionar = ctx.authorizer.can(session, ctx.actor, _PERMISO_GESTIONAR)

        root = ft.Column(spacing=theme.SPACING["md"])

        campo_numero = widgets.form_field("Número de parte")
        campo_fabricante = widgets.form_field("Fabricante")
        campo_origen = ft.Dropdown(
            label="Origen",
            value="generico",
            options=[ft.DropdownOption(key=key, text=texto) for key, texto in _ORIGENES],
        )
        error_datos = ft.Text("", color=theme.ERROR)
        equivalentes_col = ft.Column(spacing=theme.SPACING["xs"])
        compatibilidades_col = ft.Column(spacing=theme.SPACING["xs"])

        def _cargar_datos_parte() -> None:
            try:
                vista = parts.get_part(ctx.actor, product_id)
            except SistemasHNError:
                return
            campo_numero.value = vista.part_number
            campo_fabricante.value = vista.manufacturer or ""
            campo_origen.value = vista.origin

        def _guardar_datos(_: ft.Event[ft.Control]) -> None:
            try:
                parts.set_part_info(
                    ctx.actor,
                    product_id,
                    campo_numero.value or "",
                    (campo_fabricante.value or "").strip() or None,
                    campo_origen.value or "generico",
                )
            except SistemasHNError as exc:
                error_datos.value = str(exc)
                error_datos.update()
                return
            error_datos.value = ""
            error_datos.update()

        # -- Equivalencias --------------------------------------------------

        def _refrescar_equivalentes() -> None:
            equivalentes_col.controls = _render_equivalentes()
            if equivalentes_col.page is not None:
                equivalentes_col.update()

        def _quitar_equivalencias(_: ft.Event[ft.Control]) -> None:
            try:
                parts.unlink(ctx.actor, product_id)
            except SistemasHNError:
                return
            _refrescar_equivalentes()

        def _dialogo_agregar_equivalente(control: ft.Control) -> None:
            campo_texto = widgets.form_field("Buscar producto", autofocus=True)
            resultados_col = ft.Column(spacing=0)
            error = ft.Text("", color=theme.ERROR)

            def _vincular(otro_id: int) -> None:
                try:
                    parts.link_equivalent(ctx.actor, product_id, otro_id)
                except SistemasHNError as exc:
                    error.value = str(exc)
                    error.update()
                    return
                dialog.open = False
                dialog.update()
                _refrescar_equivalentes()

            def _buscar(_: ft.Event[ft.Control]) -> None:
                try:
                    pagina = catalog.search(
                        ctx.actor, campo_texto.value or "", page=1, page_size=10
                    )
                except SistemasHNError as exc:
                    error.value = str(exc)
                    error.update()
                    return
                resultados_col.controls = [
                    ft.ListTile(
                        title=ft.Text(f"{p.code} - {p.name}"),
                        on_click=lambda e, pid=p.id: _vincular(pid),
                    )
                    for p in pagina.items
                    if p.id != product_id
                ]
                resultados_col.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Agregar equivalente"),
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                campo_texto,
                                widgets.secondary_button("Buscar", _buscar),
                            ]
                        ),
                        resultados_col,
                        error,
                    ],
                    tight=True,
                ),
            )

            def _cerrar(_: ft.Event[ft.Control]) -> None:
                dialog.open = False
                dialog.update()

            dialog.actions = [widgets.secondary_button("Cerrar", _cerrar)]
            _abrir_dialogo(dialog, control)

        def _render_equivalentes() -> list[ft.Control]:
            try:
                equivalentes = parts.equivalents(ctx.actor, product_id)
            except SistemasHNError as exc:
                return [widgets.error_banner(str(exc))]

            controles: list[ft.Control] = []
            if equivalentes:
                for ref in equivalentes:
                    controles.append(ft.Text(f"{ref.code} - {ref.name}"))
            else:
                controles.append(ft.Text("Sin equivalencias.", color=theme.TEXT_MUTED))

            if puede_gestionar:
                acciones = [
                    widgets.secondary_button(
                        "Agregar equivalente", lambda e: _dialogo_agregar_equivalente(e.control)
                    )
                ]
                if equivalentes:
                    acciones.append(
                        widgets.secondary_button("Quitar de equivalencias", _quitar_equivalencias)
                    )
                controles.append(ft.Row(controls=acciones, spacing=theme.SPACING["sm"]))

            return controles

        # -- Compatibilidad --------------------------------------------------

        marcas = vehicles.list_makes(ctx.actor)
        modelos_por_id: dict[int, str] = {}
        for marca in marcas:
            for modelo in vehicles.list_models(ctx.actor, marca.id):
                modelos_por_id[modelo.id] = f"{marca.name} {modelo.name}"

        campo_marca_compat = ft.Dropdown(
            label="Marca",
            options=[ft.DropdownOption(key=str(m.id), text=m.name) for m in marcas],
        )
        campo_modelo_compat = ft.Dropdown(label="Modelo", options=[])
        campo_anio_desde = widgets.form_field("Año desde")
        campo_anio_hasta = widgets.form_field("Año hasta")
        error_compat = ft.Text("", color=theme.ERROR)

        def _cambiar_marca_compat(_: ft.Event[ft.Dropdown]) -> None:
            make_id = int(campo_marca_compat.value) if campo_marca_compat.value else None
            campo_modelo_compat.value = None
            if make_id is None:
                campo_modelo_compat.options = []
            else:
                modelos = vehicles.list_models(ctx.actor, make_id)
                campo_modelo_compat.options = [
                    ft.DropdownOption(key=str(m.id), text=m.name) for m in modelos
                ]
            if campo_modelo_compat.page is not None:
                campo_modelo_compat.update()

        campo_marca_compat.on_change = _cambiar_marca_compat

        def _refrescar_compatibilidades() -> None:
            compatibilidades_col.controls = _render_compatibilidades()
            if compatibilidades_col.page is not None:
                compatibilidades_col.update()

        def _quitar_compatibilidad(compatibility_id: int) -> None:
            try:
                parts.remove_compatibility(ctx.actor, compatibility_id)
            except SistemasHNError:
                return
            _refrescar_compatibilidades()

        def _agregar_compatibilidad(_: ft.Event[ft.Control]) -> None:
            if not campo_modelo_compat.value:
                error_compat.value = "elija un modelo"
                error_compat.update()
                return
            try:
                anio_desde = int(campo_anio_desde.value or "")
                anio_hasta = int(campo_anio_hasta.value or "")
            except ValueError:
                error_compat.value = "años inválidos"
                error_compat.update()
                return
            try:
                parts.add_compatibility(
                    ctx.actor, product_id, int(campo_modelo_compat.value), anio_desde, anio_hasta
                )
            except SistemasHNError as exc:
                error_compat.value = str(exc)
                error_compat.update()
                return
            error_compat.value = ""
            error_compat.update()
            _refrescar_compatibilidades()

        def _render_compatibilidades() -> list[ft.Control]:
            try:
                compatibilidades = parts.compatibilities(ctx.actor, product_id)
            except SistemasHNError as exc:
                return [widgets.error_banner(str(exc))]

            controles: list[ft.Control] = []
            if compatibilidades:
                for compat in compatibilidades:
                    nombre_modelo = modelos_por_id.get(compat.model_id, f"modelo {compat.model_id}")
                    fila = [
                        ft.Text(f"{nombre_modelo}: {compat.year_from}-{compat.year_to}"),
                    ]
                    if puede_gestionar:
                        fila.append(
                            ft.IconButton(
                                icon=ft.Icons.DELETE,
                                tooltip="Quitar",
                                on_click=lambda e, cid=compat.id: _quitar_compatibilidad(cid),
                            )
                        )
                    controles.append(ft.Row(controls=fila))
            else:
                controles.append(ft.Text("Sin compatibilidad registrada.", color=theme.TEXT_MUTED))

            if puede_gestionar:
                controles.append(
                    ft.Row(
                        controls=[
                            campo_marca_compat,
                            campo_modelo_compat,
                            campo_anio_desde,
                            campo_anio_hasta,
                            widgets.secondary_button("Agregar", _agregar_compatibilidad),
                        ],
                        spacing=theme.SPACING["sm"],
                        wrap=True,
                    )
                )
                controles.append(error_compat)

            return controles

        _cargar_datos_parte()
        equivalentes_col.controls = _render_equivalentes()
        compatibilidades_col.controls = _render_compatibilidades()

        secciones: list[ft.Control] = [
            ft.Row(
                controls=[campo_numero, campo_fabricante, campo_origen],
                spacing=theme.SPACING["sm"],
                wrap=True,
            ),
            error_datos,
        ]
        if puede_gestionar:
            secciones.append(widgets.primary_button("Guardar datos de parte", _guardar_datos))

        secciones.append(
            ft.Text("Equivalencias", size=theme.FONT_SUBTITLE, weight=ft.FontWeight.W_600)
        )
        secciones.append(equivalentes_col)
        secciones.append(
            ft.Text(
                "Compatibilidad con vehículos",
                size=theme.FONT_SUBTITLE,
                weight=ft.FontWeight.W_600,
            )
        )
        secciones.append(compatibilidades_col)

        root.controls = secciones
        return root
