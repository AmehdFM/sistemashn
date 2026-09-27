"""Pantallas de compras: historial y captura de una compra nueva (T3.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import flet as ft

from sistemashn.comercial.catalogo.schemas import ProductView
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.compras.schemas import (
    PurchaseInput,
    PurchaseLineInput,
    PurchaseSummary,
    PurchaseView,
)
from sistemashn.comercial.compras.service import PurchaseService
from sistemashn.comercial.contrapartes.schemas import PartyView
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ui.components import safe_page, tiene_permiso
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.money import money
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO_VER_COSTOS = "com.costos.ver"


def build_purchases_view(ctx: AppContext) -> ft.Control:
    purchases: PurchaseService = ctx.service("purchases")
    puede_ver_costos = tiene_permiso(ctx, PERMISO_VER_COSTOS)

    campo_busqueda = widgets.form_field("Buscar por número o proveedor")
    estado = {"page": 1}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True)

    def _recargar(pagina: int | None = None) -> None:
        if pagina is not None:
            estado["page"] = pagina
        root.controls = _render()
        if root.page is not None:
            root.update()

    campo_busqueda.on_submit = lambda _: _recargar(1)

    def _ver(control: ft.Control, resumen: PurchaseSummary) -> None:
        try:
            compra = purchases.get(ctx.actor, resumen.id)
        except SistemasHNError as exc:
            dialog_err = ft.AlertDialog(
                modal=True, title=ft.Text("Error"), content=widgets.error_banner(str(exc))
            )
            pagina = safe_page(control)
            if pagina is not None:
                pagina.show_dialog(dialog_err)
            return
        _mostrar_detalle(control, compra, puede_ver_costos)

    def _render() -> list[ft.Control]:
        encabezado = widgets.page_header("Compras")
        filtros = ft.Row(controls=[campo_busqueda], spacing=theme.SPACING["md"])

        try:
            pagina = purchases.list(ctx.actor, text=campo_busqueda.value or "", page=estado["page"])
        except SistemasHNError as exc:
            return [encabezado, filtros, widgets.error_banner(str(exc))]

        if not pagina.items:
            return [encabezado, filtros, widgets.empty_state("No hay compras registradas.")]

        columnas = ["Número", "Proveedor", "Fecha", "Total", "Estado", ""]
        filas: list[list[ft.Control]] = []
        for resumen in pagina.items:
            filas.append(
                [
                    ft.Text(resumen.number),
                    ft.Text(resumen.supplier_name),
                    ft.Text(resumen.purchased_at.date().isoformat()),
                    widgets.money_text(resumen.total),
                    ft.Text(resumen.status.capitalize()),
                    widgets.secondary_button("Ver", lambda e, r=resumen: _ver(e.control, r)),
                ]
            )

        tabla = widgets.paginated_table(columnas, filas, pagina, _recargar)
        return [encabezado, filtros, tabla]

    root.controls = _render()
    return root


def _mostrar_detalle(control: ft.Control, compra: PurchaseView, puede_ver_costos: bool) -> None:
    lineas: list[ft.Control] = [ft.Text("Líneas", weight=ft.FontWeight.BOLD)]
    for linea in compra.lines:
        costo = widgets.format_lempiras(linea.unit_cost) if linea.unit_cost is not None else "—"
        lineas.append(
            ft.Text(
                f"{linea.description_snapshot} · cant {linea.qty} · costo {costo} · "
                f"tasa {linea.tax_rate} · total {widgets.format_lempiras(linea.line_total)}"
            )
        )

    pagos: list[ft.Control] = [ft.Text("Pagos", weight=ft.FontWeight.BOLD)]
    if compra.payments:
        for pago in compra.payments:
            pagos.append(
                ft.Text(
                    f"{pago.method} · {widgets.format_lempiras(pago.amount)}"
                    + (f" · ref: {pago.reference}" if pago.reference else "")
                )
            )
    else:
        pagos.append(ft.Text("Sin pagos registrados."))

    resumen: list[ft.Control] = [
        ft.Text(f"Subtotal: {widgets.format_lempiras(compra.subtotal)}"),
        ft.Text(f"Impuesto: {widgets.format_lempiras(compra.tax_total)}"),
        ft.Text(f"Total: {widgets.format_lempiras(compra.total)}", weight=ft.FontWeight.BOLD),
    ]
    if compra.credit_amount > 0:
        resumen.append(ft.Text(f"Crédito: {widgets.format_lempiras(compra.credit_amount)}"))

    body = ft.Column(
        controls=[
            ft.Text(f"Compra {compra.number}", size=18, weight=ft.FontWeight.BOLD),
            *resumen,
            ft.Divider(),
            *lineas,
            ft.Divider(),
            *pagos,
        ],
        tight=True,
        scroll=ft.ScrollMode.AUTO,
        height=500,
        width=520,
    )

    dialog = ft.AlertDialog(modal=True, title=ft.Text("Detalle de compra"), content=body)

    def _cerrar(_: ft.Event[ft.Control]) -> None:
        dialog.open = False
        dialog.update()

    dialog.actions = [widgets.secondary_button("Cerrar", _cerrar)]
    pagina = safe_page(control)
    if pagina is not None:
        pagina.show_dialog(dialog)


@dataclass
class _LineaCapturada:
    product_id: int
    code: str
    name: str
    qty: Decimal
    unit_cost: Decimal
    tax_rate: Decimal


@dataclass
class _PagoCapturado:
    method: PaymentMethod
    amount: Decimal
    reference: str | None


def build_new_purchase_view(ctx: AppContext) -> ft.Control:
    """Formulario de captura de una compra nueva.

    Decisiones: el proveedor se elige buscando por nombre/RTN y seleccionando de una lista de
    resultados (sin `DatePicker`, no usado en el repo: la fecha de vencimiento de crédito se
    captura como texto `AAAA-MM-DD`). La tasa de cada línea es siempre la del producto
    encontrado (no editable desde el formulario, como simplificación del plan).
    """
    catalog: CatalogService = ctx.service("catalog")
    parties: PartyService = ctx.service("parties")
    purchases: PurchaseService = ctx.service("purchases")
    puede_ver_costos = tiene_permiso(ctx, PERMISO_VER_COSTOS)

    estado: dict = {
        "request_id": uuid4().hex,
        "proveedor": None,
        "lineas": [],
        "pagos": [],
    }

    root = ft.Column(spacing=theme.SPACING["md"], expand=True, scroll=ft.ScrollMode.AUTO)

    campo_proveedor_busqueda = widgets.form_field("Buscar proveedor por nombre o RTN")
    resultados_proveedor = ft.Column(spacing=theme.SPACING["xs"])
    proveedor_elegido = ft.Text("", weight=ft.FontWeight.BOLD)

    campo_factura = widgets.form_field("Referencia de factura del proveedor (opcional)")

    campo_codigo_producto = widgets.form_field("Código de producto")
    campo_cantidad = widgets.form_field("Cantidad")
    campo_costo = widgets.form_field("Costo unitario")
    sugerencia_costo = ft.Text("", color=theme.TEXT_MUTED)
    lista_lineas = ft.Column(spacing=theme.SPACING["xs"])

    campo_metodo_pago = ft.Dropdown(
        label="Método de pago",
        value=PaymentMethod.EFECTIVO.value,
        options=[ft.DropdownOption(key=m.value, text=m.value.capitalize()) for m in PaymentMethod],
    )
    campo_monto_pago = widgets.form_field("Monto del pago")
    campo_referencia_pago = widgets.form_field("Referencia (opcional)")
    lista_pagos = ft.Column(spacing=theme.SPACING["xs"])

    campo_vencimiento = widgets.form_field("Vencimiento de crédito (AAAA-MM-DD)")
    totales = ft.Column(spacing=2)

    error = ft.Text("", color=theme.ERROR)
    resultado_confirmacion = ft.Text("", color=theme.SUCCESS)

    def _buscar_proveedor(_: ft.Event[ft.Control]) -> None:
        texto = (campo_proveedor_busqueda.value or "").strip()
        if not texto:
            resultados_proveedor.controls = []
            resultados_proveedor.update()
            return
        try:
            pagina = parties.search(ctx.actor, texto, role="supplier", page_size=10)
        except SistemasHNError as exc:
            resultados_proveedor.controls = [widgets.error_banner(str(exc))]
            resultados_proveedor.update()
            return
        resultados_proveedor.controls = [
            widgets.secondary_button(
                f"{p.name} ({p.rtn or 'sin RTN'})", lambda e, prov=p: _elegir_proveedor(prov)
            )
            for p in pagina.items
        ]
        resultados_proveedor.update()

    def _elegir_proveedor(proveedor: PartyView) -> None:
        estado["proveedor"] = proveedor
        proveedor_elegido.value = f"Proveedor: {proveedor.name}"
        proveedor_elegido.update()
        resultados_proveedor.controls = []
        resultados_proveedor.update()

    campo_proveedor_busqueda.on_submit = _buscar_proveedor

    def _calcular_totales() -> tuple[Decimal, Decimal, Decimal, Decimal]:
        subtotal = Decimal("0")
        impuesto = Decimal("0")
        for linea in estado["lineas"]:
            sub = money(linea.qty * linea.unit_cost)
            subtotal += sub
            impuesto += money(sub * linea.tax_rate)
        subtotal = money(subtotal)
        impuesto = money(impuesto)
        total = money(subtotal + impuesto)
        pagado = money(sum((p.amount for p in estado["pagos"]), Decimal("0")))
        return subtotal, impuesto, total, pagado

    def _render_totales() -> None:
        subtotal, impuesto, total, pagado = _calcular_totales()
        controles = [
            ft.Text(f"Subtotal: {widgets.format_lempiras(subtotal)}"),
            ft.Text(f"Impuesto: {widgets.format_lempiras(impuesto)}"),
            ft.Text(f"Total: {widgets.format_lempiras(total)}", weight=ft.FontWeight.BOLD),
            ft.Text(f"Pagado: {widgets.format_lempiras(pagado)}"),
        ]
        if pagado < total:
            controles.append(ft.Text(f"Crédito: {widgets.format_lempiras(money(total - pagado))}"))
        totales.controls = controles

    def _render_lineas() -> None:
        filas: list[ft.Control] = []
        for linea in estado["lineas"]:
            filas.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            f"{linea.code} - {linea.name} · cant {linea.qty} · "
                            f"costo {widgets.format_lempiras(linea.unit_cost)}"
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="Quitar",
                            on_click=lambda e, pid=linea.product_id: _quitar_linea(pid),
                        ),
                    ],
                    spacing=theme.SPACING["sm"],
                )
            )
        lista_lineas.controls = filas
        _render_totales()

    def _quitar_linea(product_id: int) -> None:
        estado["lineas"] = [ln for ln in estado["lineas"] if ln.product_id != product_id]
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
            costo = Decimal((campo_costo.value or "").strip().replace(",", ""))
        except InvalidOperation:
            error.value = "cantidad o costo inválido"
            error.update()
            return
        try:
            producto: ProductView | None = catalog.find_by_code_or_barcode(ctx.actor, codigo)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        if producto is None:
            error.value = f"no se encontró el producto '{codigo}'"
            error.update()
            return

        error.value = ""
        estado["lineas"] = [ln for ln in estado["lineas"] if ln.product_id != producto.id] + [
            _LineaCapturada(
                product_id=producto.id,
                code=producto.code,
                name=producto.name,
                qty=cantidad,
                unit_cost=costo,
                tax_rate=producto.tax_rate,
            )
        ]
        campo_codigo_producto.value = ""
        campo_cantidad.value = ""
        campo_costo.value = ""
        sugerencia_costo.value = ""
        _render_lineas()
        error.update()
        lista_lineas.update()
        totales.update()
        campo_codigo_producto.update()
        campo_cantidad.update()
        campo_costo.update()
        sugerencia_costo.update()

    def _sugerir_costo(_: ft.Event[ft.Control]) -> None:
        if not puede_ver_costos or estado["proveedor"] is None:
            return
        codigo = (campo_codigo_producto.value or "").strip()
        if not codigo:
            return
        try:
            producto = catalog.find_by_code_or_barcode(ctx.actor, codigo)
        except SistemasHNError:
            return
        if producto is None:
            return
        try:
            historial = purchases.last_prices(ctx.actor, producto.id, limit=1)
        except SistemasHNError:
            return
        if historial:
            costo_previo = widgets.format_lempiras(historial[0].unit_cost)
            sugerencia_costo.value = f"Último costo con este proveedor: {costo_previo}"
        else:
            sugerencia_costo.value = "Sin costo histórico."
        sugerencia_costo.update()

    campo_codigo_producto.on_submit = _sugerir_costo

    def _render_pagos() -> None:
        filas: list[ft.Control] = []
        for indice, pago in enumerate(estado["pagos"]):
            filas.append(
                ft.Row(
                    controls=[
                        ft.Text(
                            f"{pago.method.value} · {widgets.format_lempiras(pago.amount)}"
                            + (f" · ref: {pago.reference}" if pago.reference else "")
                        ),
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
        _render_totales()

    def _quitar_pago(indice: int) -> None:
        del estado["pagos"][indice]
        _render_pagos()
        lista_pagos.update()
        totales.update()

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
        totales.update()
        campo_monto_pago.update()
        campo_referencia_pago.update()

    def _limpiar_formulario() -> None:
        estado["request_id"] = uuid4().hex
        estado["proveedor"] = None
        estado["lineas"] = []
        estado["pagos"] = []
        proveedor_elegido.value = ""
        campo_proveedor_busqueda.value = ""
        campo_factura.value = ""
        campo_vencimiento.value = ""
        _render_lineas()
        _render_pagos()

    def _confirmar(_: ft.Event[ft.Control]) -> None:
        resultado_confirmacion.value = ""
        if estado["proveedor"] is None:
            error.value = "seleccione un proveedor"
            error.update()
            return
        if not estado["lineas"]:
            error.value = "agregue al menos una línea"
            error.update()
            return

        _subtotal, _impuesto, total, pagado = _calcular_totales()
        fecha_vencimiento: date | None = None
        if pagado < total:
            texto_fecha = (campo_vencimiento.value or "").strip()
            if not texto_fecha:
                error.value = "una compra a crédito requiere fecha de vencimiento"
                error.update()
                return
            try:
                fecha_vencimiento = date.fromisoformat(texto_fecha)
            except ValueError:
                error.value = "fecha de vencimiento inválida, use AAAA-MM-DD"
                error.update()
                return

        try:
            data = PurchaseInput(
                supplier_id=estado["proveedor"].id,
                supplier_invoice_ref=(campo_factura.value or "").strip() or None,
                lines=[
                    PurchaseLineInput(
                        product_id=ln.product_id,
                        qty=ln.qty,
                        unit_cost=ln.unit_cost,
                        tax_rate=ln.tax_rate,
                    )
                    for ln in estado["lineas"]
                ],
                payments=[
                    PaymentInput(method=p.method, amount=p.amount, reference=p.reference)
                    for p in estado["pagos"]
                ],
                credit_due_date=fecha_vencimiento,
                request_id=estado["request_id"],
            )
        except Exception as exc:  # validación de Pydantic
            error.value = str(exc)
            error.update()
            return

        try:
            compra = purchases.confirm(ctx.actor, data)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return

        error.value = ""
        mensaje = f"Compra {compra.number} confirmada por {widgets.format_lempiras(compra.total)}."
        if compra.credit_amount > 0:
            mensaje += f" Crédito: {widgets.format_lempiras(compra.credit_amount)}."
        resultado_confirmacion.value = mensaje
        _limpiar_formulario()
        root.controls = _build_controls()
        root.update()

    def _build_controls() -> list[ft.Control]:
        _render_lineas()
        _render_pagos()
        return [
            widgets.page_header("Nueva compra"),
            ft.Text("Proveedor", weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    campo_proveedor_busqueda,
                    widgets.secondary_button("Buscar", _buscar_proveedor),
                ],
                spacing=theme.SPACING["sm"],
            ),
            resultados_proveedor,
            proveedor_elegido,
            campo_factura,
            ft.Divider(),
            ft.Text("Líneas", weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    campo_codigo_producto,
                    campo_cantidad,
                    campo_costo,
                    widgets.secondary_button("Agregar línea", _agregar_linea),
                ],
                wrap=True,
                spacing=theme.SPACING["sm"],
            ),
            sugerencia_costo,
            lista_lineas,
            ft.Divider(),
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
            campo_vencimiento,
            ft.Divider(),
            totales,
            error,
            resultado_confirmacion,
            widgets.primary_button("Confirmar compra", _confirmar),
        ]

    root.controls = _build_controls()
    return root
