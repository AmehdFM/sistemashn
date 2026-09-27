"""Pantalla de catálogo: búsqueda, alta/edición de productos, existencias y kits (T2.6a)."""

from __future__ import annotations

import contextlib
import threading
from decimal import Decimal, InvalidOperation
from pathlib import Path

import flet as ft

from sistemashn.comercial.catalogo.kits import KitService
from sistemashn.comercial.catalogo.schemas import ProductInput, ProductView
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.ui.components import (
    adjust_button,
    safe_page,
    stock_and_movements_section,
    tiene_permiso,
)
from sistemashn.comercial.ui.extensions import PRODUCT_FORM_EXTENSIONS_KEY, ProductFormExtension
from sistemashn.comercial.ui.units_categories_view import (
    open_categories_dialog,
    open_units_dialog,
)
from sistemashn.core.errors import SistemasHNError, ValidationError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_GESTIONAR = "com.catalogo.gestionar"
DEBOUNCE_SEGUNDOS = 0.3
_TASAS = (("0", "0 %"), ("0.15", "15 %"), ("0.18", "18 %"))


def parse_price(text: str, field_name: str = "el precio") -> Decimal:
    """Convierte un texto de formulario a `Decimal`; lanza `ValueError` si es inválido."""
    texto = (text or "").strip().replace(",", "")
    if not texto:
        raise ValueError(f"{field_name} es obligatorio")
    try:
        return Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} inválido: {text!r}") from exc


def parse_quantity(text: str, field_name: str = "la cantidad") -> Decimal:
    """Convierte un texto de formulario a `Decimal` de cantidad; lanza `ValueError`."""
    return parse_price(text, field_name)


def _miniatura(ctx: AppContext, image_path: str | None) -> ft.Control:
    if not image_path or ctx.data_dir is None:
        return ft.Container(width=32, height=32)
    return ft.Image(src=str(ctx.data_dir / image_path), width=32, height=32, fit=ft.BoxFit.COVER)


def build_catalog_view(ctx: AppContext) -> ft.Control:
    catalog: CatalogService = ctx.service("catalog")

    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    campo_busqueda = widgets.form_field("Buscar por código, nombre o código de barras")
    campo_incluir_inactivos = ft.Checkbox(label="Incluir inactivos", value=False)

    estado = {"page": 1, "texto": ""}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)
    _timer_ref: dict[str, threading.Timer | None] = {"t": None}

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    def _buscar_ahora() -> None:
        estado["texto"] = campo_busqueda.value or ""
        _recargar(1)

    def _on_change(_: ft.Event[ft.TextField]) -> None:
        anterior = _timer_ref["t"]
        if anterior is not None:
            anterior.cancel()
        nuevo = threading.Timer(DEBOUNCE_SEGUNDOS, _buscar_ahora)
        nuevo.daemon = True
        _timer_ref["t"] = nuevo
        nuevo.start()

    def _on_submit(_: ft.Event[ft.TextField]) -> None:
        anterior = _timer_ref["t"]
        if anterior is not None:
            anterior.cancel()
        texto = (campo_busqueda.value or "").strip()
        if texto:
            try:
                exacto = catalog.find_by_code_or_barcode(ctx.actor, texto)
            except SistemasHNError:
                exacto = None
            if exacto is not None:
                _abrir_detalle(campo_busqueda, exacto.id)
                return
        _buscar_ahora()

    campo_busqueda.on_change = _on_change
    campo_busqueda.on_submit = _on_submit

    def _on_incluir_inactivos(_: ft.Event[ft.Checkbox]) -> None:
        _recargar(1)

    campo_incluir_inactivos.on_change = _on_incluir_inactivos

    def _confirmar_cambio_activo(control: ft.Control, producto: ProductView) -> None:
        nuevo_estado = not producto.active
        verbo = "activar" if nuevo_estado else "desactivar"

        def _confirmar() -> None:
            with contextlib.suppress(SistemasHNError):
                catalog.set_active(ctx.actor, producto.id, nuevo_estado)
            _recargar()

        dialog = widgets.confirm_dialog(
            f"¿{verbo.capitalize()} producto?",
            f"¿Desea {verbo} '{producto.code} - {producto.name}'?",
            _confirmar,
            confirm_text=verbo.capitalize(),
        )
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    def _acciones_fila(producto: ProductView) -> ft.Control:
        botones = [
            ft.IconButton(
                icon=ft.Icons.VISIBILITY,
                tooltip="Ver / editar",
                on_click=lambda e, p=producto: _abrir_detalle(e.control, p.id),
            )
        ]
        if puede_gestionar:
            botones.append(
                ft.IconButton(
                    icon=ft.Icons.BLOCK if producto.active else ft.Icons.CHECK_CIRCLE,
                    tooltip="Desactivar" if producto.active else "Activar",
                    on_click=lambda e, p=producto: _confirmar_cambio_activo(e.control, p),
                )
            )
        return ft.Row(controls=botones, spacing=0)

    def _render() -> list[ft.Control]:
        acciones: list[ft.Control] = [
            widgets.secondary_button(
                "Unidades", lambda e: open_units_dialog(ctx, e.control, lambda: _recargar())
            ),
            widgets.secondary_button(
                "Categorías", lambda e: open_categories_dialog(ctx, e.control, lambda: _recargar())
            ),
        ]
        if puede_gestionar:
            acciones.append(
                widgets.primary_button("Nuevo producto", lambda e: _abrir_detalle(e.control, None))
            )
        encabezado = widgets.page_header("Catálogo", actions=acciones)
        filtros = ft.Row(
            controls=[campo_busqueda, campo_incluir_inactivos],
            spacing=theme.SPACING["md"],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        try:
            pagina = catalog.search(
                ctx.actor,
                estado["texto"],
                page=estado["page"],
                include_inactive=bool(campo_incluir_inactivos.value),
            )
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay productos que coincidan.")]

        columnas = [
            "",
            "Código",
            "Nombre",
            "Categoría",
            "Precio",
            "Disponible",
            "Estado",
            "Acciones",
        ]
        filas: list[list[ft.Control]] = []
        categorias = {
            c.id: c.name for c in catalog.list_categories(ctx.actor, include_inactive=True)
        }
        for producto in pagina.items:
            filas.append(
                [
                    _miniatura(ctx, producto.image_path),
                    ft.Text(producto.code),
                    ft.Text(producto.name),
                    ft.Text(
                        categorias.get(producto.category_id, "—") if producto.category_id else "—"
                    ),
                    widgets.money_text(producto.sale_price),
                    ft.Text(str(producto.available)),
                    ft.Text("Activo" if producto.active else "Inactivo"),
                    _acciones_fila(producto),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    def _abrir_detalle(control: ft.Control, product_id: int | None) -> None:
        _dialogo_producto(ctx, control, product_id, lambda: _recargar())

    root.controls = _render()
    return root


def _dialogo_producto(
    ctx: AppContext, control: ft.Control, product_id: int | None, on_saved
) -> None:
    catalog: CatalogService = ctx.service("catalog")
    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    producto: ProductView | None = None
    if product_id is not None:
        try:
            producto = catalog.get_product(ctx.actor, product_id)
        except SistemasHNError as exc:
            dialog_err = ft.AlertDialog(
                modal=True, title=ft.Text("Error"), content=widgets.error_banner(str(exc))
            )
            pagina = safe_page(control)
            if pagina is not None:
                pagina.show_dialog(dialog_err)
            return

    unidades = catalog.list_units(ctx.actor, include_inactive=True)
    categorias = catalog.list_categories(ctx.actor, include_inactive=True)

    campo_codigo = widgets.form_field(
        "Código", value=producto.code if producto else "", autofocus=producto is None
    )
    campo_barcode = widgets.form_field(
        "Código de barras", value=producto.barcode if producto and producto.barcode else ""
    )
    campo_nombre = widgets.form_field("Nombre", value=producto.name if producto else "")
    campo_descripcion = widgets.form_field(
        "Descripción", value=producto.description if producto and producto.description else ""
    )
    campo_categoria = ft.Dropdown(
        label="Categoría",
        value=str(producto.category_id) if producto and producto.category_id else None,
        options=[ft.DropdownOption(key=str(c.id), text=c.name) for c in categorias],
    )
    campo_unidad = ft.Dropdown(
        label="Unidad",
        value=str(producto.unit_id) if producto else None,
        options=[ft.DropdownOption(key=str(u.id), text=f"{u.code} - {u.name}") for u in unidades],
    )
    campo_isv = ft.Dropdown(
        label="ISV",
        value=str(producto.tax_rate) if producto else "0.15",
        options=[ft.DropdownOption(key=v, text=t) for v, t in _TASAS],
    )
    campo_precio = widgets.form_field(
        "Precio de venta", value=str(producto.sale_price) if producto else ""
    )
    campo_stock_min = widgets.form_field(
        "Stock mínimo", value=str(producto.min_stock) if producto else "0"
    )
    campo_es_kit = ft.Checkbox(label="Es kit", value=producto.is_kit if producto else False)
    error = ft.Text("", color=theme.ERROR)

    campos_formulario: list[ft.Control] = [
        campo_codigo,
        campo_barcode,
        campo_nombre,
        campo_descripcion,
        campo_categoria,
        campo_unidad,
        campo_isv,
        campo_precio,
        campo_stock_min,
        campo_es_kit,
    ]
    if not puede_gestionar:
        for c in campos_formulario:
            if isinstance(c, ft.TextField | ft.Dropdown | ft.Checkbox):
                c.disabled = True

    dialog = ft.AlertDialog(
        modal=True, title=ft.Text("Producto" if producto is None else producto.code)
    )
    body = ft.Column(controls=[], tight=True, scroll=ft.ScrollMode.AUTO, height=560, width=520)
    dialog.content = ft.Container(content=body, width=520)

    def _cerrar(_: ft.Event[ft.Control] | None = None) -> None:
        dialog.open = False
        dialog.update()

    def _recargar_dialogo() -> None:
        _cerrar()
        _dialogo_producto(ctx, control, product_id, on_saved)

    def _guardar(_: ft.Event[ft.Control]) -> None:
        try:
            data = ProductInput(
                code=campo_codigo.value or "",
                barcode=(campo_barcode.value or "").strip() or None,
                name=campo_nombre.value or "",
                description=(campo_descripcion.value or "").strip() or None,
                category_id=int(campo_categoria.value) if campo_categoria.value else None,
                unit_id=int(campo_unidad.value) if campo_unidad.value else 0,
                tax_rate=Decimal(campo_isv.value or "0"),
                sale_price=parse_price(campo_precio.value or ""),
                min_stock=parse_quantity(campo_stock_min.value or "0", "el stock mínimo"),
                is_kit=bool(campo_es_kit.value),
            )
        except (ValueError, ValidationError) as exc:
            error.value = str(exc)
            error.update()
            return

        try:
            if producto is None:
                nuevo_id = catalog.create_product(ctx.actor, data)
                on_saved()
                _cerrar()
                _dialogo_producto(ctx, control, nuevo_id, on_saved)
            else:
                catalog.update_product(ctx.actor, producto.id, data)
                on_saved()
                _recargar_dialogo()
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()

    contenido: list[ft.Control] = [
        ft.Text("Datos generales", weight=ft.FontWeight.BOLD),
        *campos_formulario,
        error,
    ]
    if puede_gestionar:
        contenido.append(widgets.primary_button("Guardar", _guardar))

    if producto is not None:
        contenido.append(ft.Divider())
        contenido.append(_imagen_section(ctx, producto, puede_gestionar, _recargar_dialogo))
        contenido.append(ft.Divider())
        contenido.append(stock_and_movements_section(ctx, producto.id, 1, lambda _p: None))
        boton_ajuste = adjust_button(ctx, producto.id, _recargar_dialogo)
        if boton_ajuste is not None:
            contenido.append(boton_ajuste)

        if producto.is_kit:
            contenido.append(ft.Divider())
            contenido.append(_kit_section(ctx, producto.id, puede_gestionar))

        extensiones: list[ProductFormExtension] = ctx.services.get(PRODUCT_FORM_EXTENSIONS_KEY, [])
        for extension in extensiones:
            if extension.is_visible(ctx):
                contenido.append(ft.Divider())
                contenido.append(ft.Text(extension.title, weight=ft.FontWeight.BOLD))
                contenido.append(extension.build(ctx, producto.id))

    body.controls = contenido
    dialog.actions = [widgets.secondary_button("Cerrar", _cerrar)]

    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)


def _imagen_section(
    ctx: AppContext, producto: ProductView, puede_gestionar: bool, on_saved
) -> ft.Control:
    catalog: CatalogService = ctx.service("catalog")
    mensaje = ft.Text("", color=theme.ERROR)
    vista_previa = _miniatura(ctx, producto.image_path)

    controles: list[ft.Control] = [
        ft.Text("Foto del producto", weight=ft.FontWeight.BOLD),
        vista_previa,
    ]
    if puede_gestionar:

        def _cambiar_imagen(ruta: Path) -> None:
            try:
                catalog.set_image(ctx.actor, producto.id, ruta)
                on_saved()
            except SistemasHNError as exc:
                mensaje.value = f"No se pudo actualizar la imagen: {exc}"
                mensaje.color = theme.ERROR
                mensaje.update()

        controles.append(widgets.image_picker(_cambiar_imagen, button_label="Elegir foto..."))
    controles.append(mensaje)
    return ft.Column(controls=controles, spacing=theme.SPACING["sm"])


def _kit_section(ctx: AppContext, kit_id: int, puede_gestionar: bool) -> ft.Control:
    kits: KitService = ctx.service("kits")
    catalog: CatalogService = ctx.service("catalog")

    try:
        componentes = kits.components(ctx.actor, kit_id)
    except SistemasHNError as exc:
        return widgets.error_banner(str(exc))

    lista = ft.Column(spacing=theme.SPACING["xs"])
    estado_edicion: dict[str, list[tuple[int, str, str, Decimal]]] = {
        "filas": [(c.component_id, c.code, c.name, c.qty) for c in componentes]
    }
    error = ft.Text("", color=theme.ERROR)

    campo_buscar_componente = widgets.form_field("Buscar componente por código")
    campo_cantidad = widgets.form_field("Cantidad")

    def _render_lista() -> None:
        filas: list[ft.Control] = []
        for component_id, code, name, qty in estado_edicion["filas"]:
            fila_controles: list[ft.Control] = [ft.Text(f"{code} - {name}"), ft.Text(str(qty))]
            if puede_gestionar:
                fila_controles.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        tooltip="Quitar",
                        on_click=lambda e, cid=component_id: _quitar(cid),
                    )
                )
            filas.append(ft.Row(controls=fila_controles, spacing=theme.SPACING["sm"]))
        lista.controls = filas

    def _quitar(component_id: int) -> None:
        estado_edicion["filas"] = [f for f in estado_edicion["filas"] if f[0] != component_id]
        _render_lista()
        if lista.page is not None:
            lista.update()

    def _agregar(_: ft.Event[ft.Control]) -> None:
        codigo = (campo_buscar_componente.value or "").strip()
        try:
            cantidad = parse_quantity(campo_cantidad.value or "")
        except ValueError as exc:
            error.value = str(exc)
            error.update()
            return
        if not codigo:
            error.value = "indique el código del componente"
            error.update()
            return
        try:
            encontrado = catalog.find_by_code_or_barcode(ctx.actor, codigo)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        if encontrado is None:
            error.value = f"no se encontró el producto '{codigo}'"
            error.update()
            return
        error.value = ""
        estado_edicion["filas"] = [f for f in estado_edicion["filas"] if f[0] != encontrado.id] + [
            (encontrado.id, encontrado.code, encontrado.name, cantidad)
        ]
        campo_buscar_componente.value = ""
        campo_cantidad.value = ""
        _render_lista()
        error.update()
        lista.update()
        campo_buscar_componente.update()
        campo_cantidad.update()

    def _guardar_componentes(_: ft.Event[ft.Control]) -> None:
        componentes_input = [(cid, qty) for cid, _c, _n, qty in estado_edicion["filas"]]
        try:
            kits.set_components(ctx.actor, kit_id, componentes_input)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        error.value = "Composición guardada."
        error.update()

    controles: list[ft.Control] = [ft.Text("Componentes del kit", weight=ft.FontWeight.BOLD)]
    _render_lista()
    controles.append(lista)
    if puede_gestionar:
        controles.append(
            ft.Row(
                controls=[
                    campo_buscar_componente,
                    campo_cantidad,
                    widgets.secondary_button("Agregar", _agregar),
                    widgets.primary_button("Guardar composición", _guardar_componentes),
                ],
                wrap=True,
                spacing=theme.SPACING["sm"],
            )
        )
    controles.append(error)
    return ft.Column(controls=controles, spacing=theme.SPACING["sm"])
