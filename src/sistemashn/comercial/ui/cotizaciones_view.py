"""Pantalla de cotizaciones: listado, alta y conversión a venta (T4.6)."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import flet as ft

from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.contrapartes.schemas import PartyView
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.cotizaciones.schemas import QuoteInput, QuoteLineInput, QuoteSummary
from sistemashn.comercial.cotizaciones.service import QuoteService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.presentacion import PresentationSnapshot
from sistemashn.comercial.ui.components import safe_page, tiene_permiso
from sistemashn.comercial.ventas.errors import QuoteConversionMismatch
from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
from sistemashn.comercial.ventas.service import SaleService
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.money import money
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_GESTIONAR = "com.cotizaciones.gestionar"
_ESTADOS = (
    ("", "Todas"),
    ("abierta", "Abierta"),
    ("vencida", "Vencida"),
    ("convertida", "Convertida"),
    ("cancelada", "Cancelada"),
)


@dataclass
class _LineaCapturada:
    product_id: int
    code: str
    name: str
    qty: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    presentation: PresentationSnapshot | None = None


@dataclass
class _PagoCapturado:
    method: PaymentMethod
    amount: Decimal
    reference: str | None


def build_quotes_view(ctx: AppContext) -> ft.Control:
    quotes: QuoteService = ctx.service("quotes")
    puede_gestionar = tiene_permiso(ctx, PERMISO_GESTIONAR)

    campo_busqueda = widgets.form_field("Buscar por número")
    campo_estado = ft.Dropdown(
        label="Estado", value="", options=[ft.DropdownOption(key=v, text=t) for v, t in _ESTADOS]
    )

    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    campo_busqueda.on_submit = lambda _: _recargar(1)
    campo_estado.on_change = lambda _: _recargar(1)

    def _confirmar_cancelar(control: ft.Control, resumen: QuoteSummary) -> None:
        def _confirmar() -> None:
            with contextlib.suppress(SistemasHNError):
                quotes.cancel(ctx.actor, resumen.id)
            _recargar()

        dialog = widgets.confirm_dialog(
            "¿Cancelar cotización?",
            f"¿Desea cancelar la cotización {resumen.number}?",
            _confirmar,
            confirm_text="Cancelar cotización",
        )
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    def _acciones_fila(resumen: QuoteSummary) -> ft.Control:
        botones: list[ft.Control] = []
        if resumen.status == "abierta":
            botones.append(
                widgets.secondary_button(
                    "Convertir a venta",
                    lambda e, r=resumen: _dialogo_conversion(ctx, e.control, r.id, _recargar),
                )
            )
            if puede_gestionar:
                botones.append(
                    widgets.secondary_button(
                        "Cancelar", lambda e, r=resumen: _confirmar_cancelar(e.control, r)
                    )
                )
        return ft.Row(controls=botones, spacing=theme.SPACING["sm"], wrap=True)

    def _render() -> list[ft.Control]:
        acciones: list[ft.Control] = []
        if puede_gestionar:
            acciones.append(
                widgets.primary_button(
                    "Nueva cotización",
                    lambda e: _dialogo_nueva_cotizacion(ctx, e.control, _recargar),
                )
            )
        encabezado = widgets.page_header("Cotizaciones", actions=acciones)
        filtros = ft.Row(
            controls=[campo_busqueda, campo_estado],
            spacing=theme.SPACING["md"],
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        try:
            pagina = quotes.list(
                ctx.actor,
                status=campo_estado.value or None,
                text=campo_busqueda.value or "",
                page=estado["page"],
            )
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay cotizaciones registradas.")]

        columnas = ["Número", "Cliente", "Vigencia", "Total", "Estado", ""]
        filas: list[list[ft.Control]] = []
        for resumen in pagina.items:
            filas.append(
                [
                    ft.Text(resumen.number),
                    ft.Text(str(resumen.customer_id) if resumen.customer_id else "—"),
                    ft.Text(resumen.valid_until.isoformat()),
                    widgets.money_text(resumen.total),
                    ft.Text(resumen.status.capitalize()),
                    _acciones_fila(resumen),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    root.controls = _render()
    return root


def _dialogo_nueva_cotizacion(ctx: AppContext, control: ft.Control, on_saved: Callable) -> None:
    """Formulario de captura de una cotización nueva (mismo patrón de líneas del POS/compras)."""
    catalog: CatalogService = ctx.service("catalog")
    parties: PartyService = ctx.service("parties")
    quotes: QuoteService = ctx.service("quotes")
    fer_catalog = ctx.services.get("fer_catalog")
    fer_lines = ctx.services.get("fer_lines")

    estado: dict = {"cliente": None, "lineas": []}

    campo_cliente_busqueda = widgets.form_field("Buscar cliente por nombre o RTN (opcional)")
    resultados_cliente = ft.Column(spacing=theme.SPACING["xs"])
    cliente_elegido = ft.Text("", weight=ft.FontWeight.BOLD)

    campo_codigo_producto = widgets.form_field(
        "SKU o código de empaque" if fer_lines is not None else "Código de producto"
    )
    campo_cantidad = widgets.form_field("Cantidad")
    lista_lineas = ft.Column(spacing=theme.SPACING["xs"])

    campo_vigencia = widgets.form_field("Vigente hasta (AAAA-MM-DD)")
    campo_apartar = ft.Checkbox(label="Apartar inventario", value=False)
    totales = ft.Column(spacing=2)
    error = ft.Text("", color=theme.ERROR)

    def _buscar_cliente(_: ft.Event[ft.Control]) -> None:
        texto = (campo_cliente_busqueda.value or "").strip()
        if not texto:
            resultados_cliente.controls = []
            resultados_cliente.update()
            return
        try:
            pagina = parties.search(ctx.actor, texto, role="customer", page_size=10)
        except SistemasHNError as exc:
            resultados_cliente.controls = [widgets.error_banner(str(exc))]
            resultados_cliente.update()
            return
        resultados_cliente.controls = [
            widgets.secondary_button(
                f"{p.name} ({p.rtn or 'sin RTN'})", lambda e, c=p: _elegir_cliente(c)
            )
            for p in pagina.items
        ]
        resultados_cliente.update()

    def _elegir_cliente(cliente: PartyView) -> None:
        estado["cliente"] = cliente
        cliente_elegido.value = f"Cliente: {cliente.name}"
        cliente_elegido.update()
        resultados_cliente.controls = []
        resultados_cliente.update()

    campo_cliente_busqueda.on_submit = _buscar_cliente

    def _calcular_totales() -> tuple[Decimal, Decimal, Decimal]:
        subtotal = Decimal("0")
        impuesto = Decimal("0")
        for linea in estado["lineas"]:
            sub = money(linea.qty * linea.unit_price)
            subtotal += sub
            impuesto += money(sub * linea.tax_rate)
        subtotal = money(subtotal)
        impuesto = money(impuesto)
        return subtotal, impuesto, money(subtotal + impuesto)

    def _render_totales() -> None:
        subtotal, impuesto, total = _calcular_totales()
        totales.controls = [
            ft.Text(f"Subtotal: {widgets.format_lempiras(subtotal)}"),
            ft.Text(f"Impuesto: {widgets.format_lempiras(impuesto)}"),
            ft.Text(f"Total: {widgets.format_lempiras(total)}", weight=ft.FontWeight.BOLD),
        ]

    def _render_lineas() -> None:
        filas: list[ft.Control] = []
        for linea in estado["lineas"]:
            pack_id = linea.presentation.pack_id if linea.presentation else None
            detail = (
                f" · {linea.presentation.quantity} {linea.presentation.label}"
                if linea.presentation
                else ""
            )
            filas.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            f"{linea.code} - {linea.name}{detail} · base {linea.qty} · "
                            f"precio {widgets.format_lempiras(linea.unit_price)}"
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="Quitar",
                            on_click=lambda e, pid=linea.product_id, pack=pack_id: _quitar_linea(
                                pid, pack
                            ),
                        ),
                    ],
                    spacing=theme.SPACING["sm"],
                )
            )
        lista_lineas.controls = filas
        _render_totales()

    def _quitar_linea(product_id: int, pack_id: int | None = None) -> None:
        estado["lineas"] = [
            ln
            for ln in estado["lineas"]
            if (ln.product_id, ln.presentation.pack_id if ln.presentation else None)
            != (product_id, pack_id)
        ]
        _render_lineas()
        lista_lineas.update()
        totales.update()

    def _agregar_linea(_: ft.Event[ft.Control]) -> None:
        codigo = (campo_codigo_producto.value or "").strip()
        if not codigo:
            error.value = "indique el código del producto"
            error.update()
            return
        try:
            cantidad = Decimal((campo_cantidad.value or "").strip().replace(",", ""))
        except InvalidOperation:
            error.value = "cantidad inválida"
            error.update()
            return
        try:
            captured = None
            if fer_catalog is not None and fer_lines is not None:
                pack_id = int(codigo[5:]) if codigo.startswith("PACK:") else None
                pack = (
                    None if pack_id is not None else fer_catalog.resolve_barcode(ctx.actor, codigo)
                )
                if pack_id is not None or pack is not None:
                    captured = fer_lines.quote_line(
                        ctx.actor, pack_id if pack_id is not None else pack.id, cantidad
                    )
                    producto = catalog.get_product(ctx.actor, captured.product_id)
                else:
                    producto = catalog.find_by_code_or_barcode(ctx.actor, codigo)
            else:
                producto = catalog.find_by_code_or_barcode(ctx.actor, codigo)
        except (SistemasHNError, ValueError) as exc:
            error.value = str(exc)
            error.update()
            return
        if producto is None:
            error.value = f"no se encontró el producto '{codigo}'"
            error.update()
            return

        error.value = ""
        pack_id = captured.presentation.pack_id if captured else None
        estado["lineas"] = [
            ln
            for ln in estado["lineas"]
            if (ln.product_id, ln.presentation.pack_id if ln.presentation else None)
            != (producto.id, pack_id)
        ] + [
            _LineaCapturada(
                product_id=producto.id,
                code=producto.code,
                name=producto.name,
                qty=captured.qty if captured else cantidad,
                unit_price=captured.unit_price if captured else producto.sale_price,
                tax_rate=producto.tax_rate,
                presentation=captured.presentation if captured else None,
            )
        ]
        campo_codigo_producto.value = ""
        campo_cantidad.value = ""
        _render_lineas()
        error.update()
        lista_lineas.update()
        totales.update()
        campo_codigo_producto.update()
        campo_cantidad.update()

    def _elegir_presentacion(event: ft.Event[ft.Control]) -> None:
        if fer_catalog is None or fer_lines is None:
            return
        codigo = (campo_codigo_producto.value or "").strip()
        try:
            pack_found = fer_catalog.resolve_barcode(ctx.actor, codigo)
            producto = (
                catalog.get_product(ctx.actor, pack_found.product_id)
                if pack_found is not None
                else catalog.find_by_code_or_barcode(ctx.actor, codigo)
            )
            if producto is None:
                raise ValueError("indique el SKU o código de un artículo existente")
            packs = fer_catalog.list_packs(ctx.actor, producto.id)
            if not packs:
                raise ValueError("este artículo no tiene presentaciones adicionales")
        except (SistemasHNError, ValueError) as exc:
            error.value = str(exc)
            error.update()
            return

        chooser = ft.AlertDialog(
            modal=True,
            title=ft.Text("Elegir presentación"),
            content=ft.Column(tight=True, spacing=theme.SPACING["sm"]),
        )

        def _seleccionar(pack_code: str | None, pack_id: int) -> None:
            campo_codigo_producto.value = pack_code or f"PACK:{pack_id}"
            campo_codigo_producto.update()
            chooser.open = False
            chooser.update()

        chooser.content.controls = [
            widgets.secondary_button(
                f"{pack.label} · × {pack.factor_base}",
                lambda e, code=pack.code, pid=pack.id: _seleccionar(code, pid),
            )
            for pack in packs
        ]

        def _cerrar_chooser(_: ft.Event[ft.Control]) -> None:
            chooser.open = False
            chooser.update()

        chooser.actions = [widgets.secondary_button("Cerrar", _cerrar_chooser)]
        pagina = safe_page(event.control)
        if pagina is not None:
            pagina.show_dialog(chooser)

    dialog = ft.AlertDialog(modal=True, title=ft.Text("Nueva cotización"))
    body = ft.Column(controls=[], tight=True, scroll=ft.ScrollMode.AUTO, height=560, width=520)
    dialog.content = ft.Container(content=body, width=520)

    def _cerrar(_: ft.Event[ft.Control] | None = None) -> None:
        dialog.open = False
        dialog.update()

    def _guardar(_: ft.Event[ft.Control]) -> None:
        if not estado["lineas"]:
            error.value = "agregue al menos una línea"
            error.update()
            return
        texto_fecha = (campo_vigencia.value or "").strip()
        if not texto_fecha:
            error.value = "indique la fecha de vigencia"
            error.update()
            return
        try:
            vigencia = date.fromisoformat(texto_fecha)
        except ValueError:
            error.value = "fecha de vigencia inválida, use AAAA-MM-DD"
            error.update()
            return

        try:
            data = QuoteInput(
                customer_id=estado["cliente"].id if estado["cliente"] is not None else None,
                lines=[
                    QuoteLineInput(
                        product_id=ln.product_id,
                        qty=ln.qty,
                        unit_price=ln.unit_price,
                        presentation=ln.presentation,
                    )
                    for ln in estado["lineas"]
                ],
                valid_until=vigencia,
                reserve=bool(campo_apartar.value),
                request_id=uuid4().hex,
            )
        except Exception as exc:  # validación de Pydantic
            error.value = str(exc)
            error.update()
            return

        try:
            quotes.create(ctx.actor, data)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return

        on_saved()
        _cerrar()

    body.controls = [
        ft.Text("Cliente", weight=ft.FontWeight.BOLD),
        ft.Row(
            controls=[campo_cliente_busqueda, widgets.secondary_button("Buscar", _buscar_cliente)],
            spacing=theme.SPACING["sm"],
        ),
        resultados_cliente,
        cliente_elegido,
        ft.Divider(),
        ft.Text("Líneas", weight=ft.FontWeight.BOLD),
        ft.Row(
            controls=[
                campo_codigo_producto,
                campo_cantidad,
                *(
                    [widgets.secondary_button("Elegir empaque", _elegir_presentacion)]
                    if fer_lines is not None
                    else []
                ),
                widgets.secondary_button("Agregar línea", _agregar_linea),
            ],
            wrap=True,
            spacing=theme.SPACING["sm"],
        ),
        lista_lineas,
        campo_vigencia,
        campo_apartar,
        ft.Divider(),
        totales,
        error,
    ]
    _render_lineas()
    dialog.actions = [
        widgets.secondary_button("Cancelar", _cerrar),
        widgets.primary_button("Guardar", _guardar),
    ]

    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)


def _dialogo_conversion(
    ctx: AppContext, control: ft.Control, quote_id: int, on_saved: Callable
) -> None:
    """Diálogo de conversión de una cotización a venta, con captura mínima de pagos.

    Decisión: se reutiliza el mismo mini-formulario de pagos (método/monto/referencia) del
    resto de la aplicación, en vez de asumir "efectivo por el total", para permitir pagos
    mixtos también al convertir.
    """
    quotes: QuoteService = ctx.service("quotes")
    sales: SaleService = ctx.service("sales")

    try:
        cotizacion = quotes.get(ctx.actor, quote_id)
    except SistemasHNError as exc:
        dialog_err = ft.AlertDialog(
            modal=True, title=ft.Text("Error"), content=widgets.error_banner(str(exc))
        )
        pagina = safe_page(control)
        if pagina is not None:
            pagina.show_dialog(dialog_err)
        return

    estado: dict = {"pagos": [], "request_id": uuid4().hex, "accept_changes": False}

    campo_metodo_pago = ft.Dropdown(
        label="Método de pago",
        value=PaymentMethod.EFECTIVO.value,
        options=[ft.DropdownOption(key=m.value, text=m.value.capitalize()) for m in PaymentMethod],
    )
    campo_monto_pago = widgets.form_field("Monto del pago", value=str(cotizacion.total))
    campo_referencia_pago = widgets.form_field("Referencia (opcional)")
    lista_pagos = ft.Column(spacing=theme.SPACING["xs"])
    aviso_diferencias = ft.Column(spacing=theme.SPACING["xs"])
    error = ft.Text("", color=theme.ERROR)

    def _render_pagos() -> None:
        filas: list[ft.Control] = []
        for indice, pago in enumerate(estado["pagos"]):
            filas.append(
                ft.Row(
                    controls=[
                        ft.Text(f"{pago.method.value} · {widgets.format_lempiras(pago.amount)}"),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="Quitar",
                            on_click=lambda e, i=indice: _quitar_pago(i),
                        ),
                    ],
                    spacing=theme.SPACING["sm"],
                )
            )
        lista_pagos.controls = filas

    def _quitar_pago(indice: int) -> None:
        del estado["pagos"][indice]
        _render_pagos()
        lista_pagos.update()

    def _agregar_pago(_: ft.Event[ft.Control]) -> None:
        try:
            monto = Decimal((campo_monto_pago.value or "").strip().replace(",", ""))
        except InvalidOperation:
            error.value = "el monto del pago es inválido"
            error.update()
            return
        if monto <= 0:
            error.value = "el monto del pago debe ser mayor a cero"
            error.update()
            return
        try:
            metodo = PaymentMethod(campo_metodo_pago.value)
        except ValueError:
            error.value = "método de pago inválido"
            error.update()
            return
        error.value = ""
        estado["pagos"].append(
            _PagoCapturado(
                method=metodo,
                amount=money(monto),
                reference=(campo_referencia_pago.value or "").strip() or None,
            )
        )
        campo_monto_pago.value = ""
        campo_referencia_pago.value = ""
        _render_pagos()
        error.update()
        lista_pagos.update()
        campo_monto_pago.update()
        campo_referencia_pago.update()

    dialog = ft.AlertDialog(modal=True, title=ft.Text(f"Convertir {cotizacion.number} a venta"))
    body = ft.Column(controls=[], tight=True, scroll=ft.ScrollMode.AUTO, height=480, width=480)
    dialog.content = ft.Container(content=body, width=480)

    def _cerrar(_: ft.Event[ft.Control] | None = None) -> None:
        dialog.open = False
        dialog.update()

    def _intentar_convertir(_: ft.Event[ft.Control] | None = None) -> None:
        try:
            data = SaleInput(
                customer_id=cotizacion.customer_id,
                quote_id=cotizacion.id,
                lines=[
                    SaleLineInput(
                        product_id=ln.product_id,
                        qty=ln.qty,
                        unit_price=ln.unit_price,
                        presentation=ln.presentation,
                    )
                    for ln in cotizacion.lines
                ],
                payments=[
                    PaymentInput(method=p.method, amount=p.amount, reference=p.reference)
                    for p in estado["pagos"]
                ],
                accept_changes=estado["accept_changes"],
                request_id=estado["request_id"],
            )
        except Exception as exc:  # validación de Pydantic
            error.value = str(exc)
            error.update()
            return

        try:
            sales.confirm(ctx.actor, data)
        except QuoteConversionMismatch as exc:
            error.value = ""
            filas_dif = ft.Column(
                controls=[
                    ft.Text(
                        f"- producto {d.product_id} ({d.field}): "
                        f"esperado {d.expected}, actual {d.actual}"
                    )
                    for d in exc.differences
                ]
            )
            aviso_diferencias.controls = [
                widgets.error_banner("La cotización cambió desde que se creó:"),
                filas_dif,
                widgets.secondary_button(
                    "Convertir de todos modos", lambda e: _forzar_conversion()
                ),
            ]
            body.update()
            return
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return

        on_saved()
        _cerrar()

    def _forzar_conversion() -> None:
        estado["accept_changes"] = True
        aviso_diferencias.controls = []
        _intentar_convertir()

    body.controls = [
        ft.Text(f"Total de la cotización: {widgets.format_lempiras(cotizacion.total)}"),
        ft.Text("Pagos", weight=ft.FontWeight.BOLD),
        ft.Row(
            controls=[
                campo_metodo_pago,
                campo_monto_pago,
                campo_referencia_pago,
                widgets.secondary_button("Agregar pago", _agregar_pago),
            ],
            wrap=True,
            spacing=theme.SPACING["sm"],
        ),
        lista_pagos,
        aviso_diferencias,
        error,
    ]
    _render_pagos()
    dialog.actions = [
        widgets.secondary_button("Cancelar", _cerrar),
        widgets.primary_button("Convertir", _intentar_convertir),
    ]

    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)
