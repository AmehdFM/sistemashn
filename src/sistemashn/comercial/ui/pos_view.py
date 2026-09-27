"""Pantalla de punto de venta (POS): captura y confirmación de una venta (T4.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import flet as ft

from sistemashn.comercial.caja.service import CashService
from sistemashn.comercial.catalogo.schemas import ProductView
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.contrapartes.schemas import PartyView
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.fiscal.service import FiscalService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ui.components import safe_page
from sistemashn.comercial.ui.parked_sales_store import ParkedSalesStore
from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput, SaleView
from sistemashn.comercial.ventas.service import SaleService
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.money import money
from sistemashn.core.settings.schemas import DEFAULT_PRINT_RECEIPT_POLICY
from sistemashn.core.settings.service import SettingsService
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


@dataclass
class _LineaCapturada:
    product_id: int
    code: str
    name: str
    qty: Decimal
    unit_price: Decimal
    tax_rate: Decimal


@dataclass
class _PagoCapturado:
    method: PaymentMethod
    amount: Decimal
    reference: str | None


def build_pos_view(ctx: AppContext) -> ft.Control:
    """Formulario de venta rápida: lector USB / código de producto, cliente opcional y pagos
    mixtos con cálculo de vuelto en vivo.

    Decisión: el backend actual (`SaleService.confirm`) no exige una sesión de caja abierta para
    registrar los pagos en efectivo (ver comentario en `ventas/service.py`); esta pantalla solo
    avisa cuando no hay caja abierta, sin bloquear la venta.
    """
    catalog: CatalogService = ctx.service("catalog")
    parties: PartyService = ctx.service("parties")
    sales: SaleService = ctx.service("sales")
    cash: CashService = ctx.service("cash")
    fiscal: FiscalService = ctx.service("fiscal")
    parked: ParkedSalesStore = ctx.service("parked_sales")
    settings_service: SettingsService = ctx.service("settings")

    def _nuevo_estado() -> dict:
        return {
            "request_id": uuid4().hex,
            "cliente": None,
            "lineas": [],
            "pagos": [],
            "cash_session_id": None,
        }

    estado: dict = _nuevo_estado()

    root = ft.Column(spacing=theme.SPACING["md"], expand=True, scroll=ft.ScrollMode.AUTO)

    aviso_caja = ft.Text("", color=theme.ERROR)
    boton_ventas_espera = widgets.secondary_button("Ventas en espera (0)", lambda e: None)

    campo_cliente_busqueda = widgets.form_field("Buscar cliente por nombre o RTN (opcional)")
    resultados_cliente = ft.Column(spacing=theme.SPACING["xs"])
    cliente_elegido = ft.Text("", weight=ft.FontWeight.BOLD)

    campo_codigo_producto = widgets.form_field("Código o código de barras (Enter para agregar)")
    campo_cantidad = widgets.form_field("Cantidad", value="1")
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

    def _actualizar_sesion_caja() -> None:
        try:
            sesion = cash.current(ctx.actor)
        except SistemasHNError:
            sesion = None
        estado["cash_session_id"] = sesion.id if sesion is not None else None
        aviso_caja.value = "" if sesion is not None else "No hay caja abierta."

    _actualizar_sesion_caja()

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

    def _calcular_totales() -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        subtotal = Decimal("0")
        impuesto = Decimal("0")
        for linea in estado["lineas"]:
            sub = money(linea.qty * linea.unit_price)
            subtotal += sub
            impuesto += money(sub * linea.tax_rate)
        subtotal = money(subtotal)
        impuesto = money(impuesto)
        total = money(subtotal + impuesto)
        pagado = money(sum((p.amount for p in estado["pagos"]), Decimal("0")))
        efectivo = money(
            sum(
                (p.amount for p in estado["pagos"] if p.method == PaymentMethod.EFECTIVO),
                Decimal("0"),
            )
        )
        vuelto = Decimal("0.00")
        if pagado > total:
            exceso = money(pagado - total)
            vuelto = min(exceso, efectivo)
        return subtotal, impuesto, total, pagado, vuelto

    def _render_totales() -> None:
        subtotal, impuesto, total, pagado, vuelto = _calcular_totales()
        controles = [
            ft.Text(f"Subtotal: {widgets.format_lempiras(subtotal)}"),
            ft.Text(f"Impuesto: {widgets.format_lempiras(impuesto)}"),
            ft.Text(f"Total: {widgets.format_lempiras(total)}", weight=ft.FontWeight.BOLD),
            ft.Text(f"Pagado: {widgets.format_lempiras(pagado)}"),
        ]
        if vuelto > 0:
            controles.append(
                ft.Text(f"Vuelto: {widgets.format_lempiras(vuelto)}", color=theme.SUCCESS)
            )
        elif pagado < total:
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
                            f"precio {widgets.format_lempiras(linea.unit_price)}"
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

    def _agregar_producto(producto: ProductView, cantidad: Decimal) -> None:
        estado["lineas"] = [ln for ln in estado["lineas"] if ln.product_id != producto.id] + [
            _LineaCapturada(
                product_id=producto.id,
                code=producto.code,
                name=producto.name,
                qty=cantidad,
                unit_price=producto.sale_price,
                tax_rate=producto.tax_rate,
            )
        ]
        campo_codigo_producto.value = ""
        campo_cantidad.value = "1"
        _render_lineas()
        error.value = ""
        error.update()
        lista_lineas.update()
        totales.update()
        campo_codigo_producto.update()
        campo_cantidad.update()

    def _on_submit_codigo(_: ft.Event[ft.TextField]) -> None:
        codigo = (campo_codigo_producto.value or "").strip()
        if not codigo:
            return
        try:
            cantidad = Decimal((campo_cantidad.value or "1").strip().replace(",", ""))
        except InvalidOperation:
            error.value = "cantidad inválida"
            error.update()
            return
        try:
            producto = catalog.find_by_code_or_barcode(ctx.actor, codigo)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        if producto is None:
            error.value = f"no se encontró el producto '{codigo}'"
            error.update()
            return
        _agregar_producto(producto, cantidad)

    campo_codigo_producto.on_submit = _on_submit_codigo

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
        estado.clear()
        estado.update(_nuevo_estado())
        cliente_elegido.value = ""
        campo_cliente_busqueda.value = ""
        campo_vencimiento.value = ""
        _actualizar_sesion_caja()
        _render_lineas()
        _render_pagos()

    def _tiene_venta_en_curso() -> bool:
        return bool(estado["lineas"]) or bool(estado["pagos"])

    def _actualizar_boton_espera() -> None:
        cantidad = len(parked.list_for_user(ctx.actor.user_id)) if ctx.actor is not None else 0
        boton_ventas_espera.content = f"Ventas en espera ({cantidad})"

    def _aparcar_venta(_: ft.Event[ft.Control]) -> None:
        if not _tiene_venta_en_curso():
            error.value = "no hay ninguna línea que aparcar"
            error.update()
            return
        if ctx.actor is not None:
            parked.park(ctx.actor.user_id, estado)
        _limpiar_formulario()
        _actualizar_boton_espera()
        boton_ventas_espera.update()
        root.controls = _build_controls()
        root.update()

    def _retomar_borrador(park_id: str) -> None:
        borrador = parked.retrieve(park_id)
        if borrador is None:
            return
        parked.discard(park_id)
        estado.clear()
        estado.update(borrador)
        cliente_elegido.value = (
            f"Cliente: {estado['cliente'].name}" if estado["cliente"] is not None else ""
        )
        campo_vencimiento.value = ""
        _actualizar_sesion_caja()
        _actualizar_boton_espera()
        root.controls = _build_controls()
        root.update()

    def _abrir_ventas_en_espera(control: ft.Event[ft.Control]) -> None:
        if ctx.actor is None:
            return
        borradores = parked.list_for_user(ctx.actor.user_id)

        def _hacer_retomar(park_id: str) -> None:
            def _al_confirmar() -> None:
                _retomar_borrador(park_id)

            if _tiene_venta_en_curso():
                pagina = safe_page(control.control)
                if pagina is not None:
                    pagina.show_dialog(
                        widgets.confirm_dialog(
                            "Reemplazar venta en curso",
                            "Hay una venta sin aparcar en curso. ¿Retomar el borrador de todos "
                            "modos y descartar lo que no ha guardado?",
                            _al_confirmar,
                        )
                    )
            else:
                _al_confirmar()
            dialog.open = False
            dialog.update()

        filas: list[ft.Control] = []
        for park_id, borrador in borradores:
            cantidad_lineas = len(borrador.get("lineas", []))
            filas.append(
                ft.Row(
                    controls=[
                        ft.Text(f"{cantidad_lineas} línea(s)"),
                        widgets.secondary_button(
                            "Retomar", lambda e, pid=park_id: _hacer_retomar(pid)
                        ),
                    ],
                    spacing=theme.SPACING["sm"],
                )
            )
        if not filas:
            filas.append(ft.Text("No hay ventas en espera."))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ventas en espera"),
            content=ft.Column(controls=filas, tight=True, spacing=theme.SPACING["xs"]),
            actions=[widgets.secondary_button("Cerrar", lambda e: _cerrar_dialogo())],
        )

        def _cerrar_dialogo() -> None:
            dialog.open = False
            dialog.update()

        pagina = safe_page(control.control)
        if pagina is not None:
            pagina.show_dialog(dialog)

    boton_ventas_espera.on_click = _abrir_ventas_en_espera

    def _construir_sale_input() -> SaleInput | None:
        if not estado["lineas"]:
            error.value = "agregue al menos una línea"
            error.update()
            return None

        _subtotal, _impuesto, total, pagado, _vuelto = _calcular_totales()
        fecha_vencimiento: date | None = None
        if pagado < total:
            if estado["cliente"] is None:
                error.value = "una venta a crédito requiere seleccionar un cliente"
                error.update()
                return None
            texto_fecha = (campo_vencimiento.value or "").strip()
            if not texto_fecha:
                error.value = "una venta a crédito requiere fecha de vencimiento"
                error.update()
                return None
            try:
                fecha_vencimiento = date.fromisoformat(texto_fecha)
            except ValueError:
                error.value = "fecha de vencimiento inválida, use AAAA-MM-DD"
                error.update()
                return None

        try:
            return SaleInput(
                customer_id=estado["cliente"].id if estado["cliente"] is not None else None,
                lines=[
                    SaleLineInput(product_id=ln.product_id, qty=ln.qty, unit_price=ln.unit_price)
                    for ln in estado["lineas"]
                ],
                payments=[
                    PaymentInput(method=p.method, amount=p.amount, reference=p.reference)
                    for p in estado["pagos"]
                ],
                credit_due_date=fecha_vencimiento,
                cash_session_id=estado["cash_session_id"],
                request_id=estado["request_id"],
            )
        except Exception as exc:  # validación de Pydantic
            error.value = str(exc)
            error.update()
            return None

    def _politica_impresion() -> str:
        try:
            negocio = settings_service.get_business()
        except SistemasHNError:
            negocio = None
        return negocio.print_receipt_policy if negocio is not None else DEFAULT_PRINT_RECEIPT_POLICY

    def _imprimir_recibo(_: ft.Event[ft.Control]) -> None:
        # No hay integración de impresora real todavía (fuera de alcance de T7.5): este botón
        # es un placeholder que no hace nada, salvo dejar constancia de la intención del cajero.
        pass

    def _mostrar_resultado(venta: SaleView) -> None:
        politica = _politica_impresion()
        controles: list[ft.Control] = [
            widgets.page_header("Venta confirmada"),
            ft.Text(f"Venta {venta.number}"),
            ft.Text(
                widgets.format_lempiras(venta.change_amount),
                size=32,
                weight=ft.FontWeight.BOLD,
                color=theme.SUCCESS,
            ),
            ft.Text("Vuelto", color=theme.TEXT_MUTED),
        ]
        if venta.credit_amount > 0:
            controles.append(
                ft.Text(f"Queda a crédito: {widgets.format_lempiras(venta.credit_amount)}")
            )
        # Con política 'auto' no se pregunta: se entiende que ya se imprimió sin pedir
        # confirmación al cajero, así que no se muestra el botón en ese caso. Con 'never'
        # tampoco se muestra.
        if politica == "ask":
            controles.append(widgets.secondary_button("Imprimir", _imprimir_recibo))
        controles.append(widgets.primary_button("Nueva venta", _nueva_venta))
        root.controls = controles
        root.update()

    def _nueva_venta(_: ft.Event[ft.Control]) -> None:
        _limpiar_formulario()
        root.controls = _build_controls()
        root.update()

    def _confirmar(evento: ft.Event[ft.Control]) -> None:
        resultado_confirmacion.value = ""
        data = _construir_sale_input()
        if data is None:
            return

        _subtotal, _impuesto, total, pagado, vuelto = _calcular_totales()

        def _confirmar_de_verdad() -> None:
            try:
                venta = sales.confirm(ctx.actor, data)
            except SistemasHNError as exc:
                error.value = str(exc)
                error.update()
                return
            error.value = ""
            _mostrar_resultado(venta)

        filas_resumen: list[ft.Control] = [
            ft.Text(
                f"{ln.code} - {ln.name} · cant {ln.qty} · {widgets.format_lempiras(ln.unit_price)}"
            )
            for ln in estado["lineas"]
        ]
        filas_resumen.append(ft.Divider())
        filas_resumen.append(ft.Text(f"Total: {widgets.format_lempiras(total)}"))
        for pago in estado["pagos"]:
            filas_resumen.append(
                ft.Text(f"Pago {pago.method.value}: {widgets.format_lempiras(pago.amount)}")
            )
        if vuelto > 0:
            filas_resumen.append(ft.Text(f"Vuelto: {widgets.format_lempiras(vuelto)}"))
        elif pagado < total:
            filas_resumen.append(
                ft.Text(f"Crédito: {widgets.format_lempiras(money(total - pagado))}")
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar venta"),
            content=ft.Column(controls=filas_resumen, tight=True, spacing=theme.SPACING["xs"]),
        )

        def _volver_a_editar(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()

        def _confirmar_dialogo(_: ft.Event[ft.Control]) -> None:
            dialog.open = False
            dialog.update()
            _confirmar_de_verdad()

        dialog.actions = [
            widgets.secondary_button("Volver a editar", _volver_a_editar),
            widgets.primary_button("Confirmar", _confirmar_dialogo),
        ]
        pagina = safe_page(evento.control)
        if pagina is not None:
            pagina.show_dialog(dialog)
        else:
            # Sin página adjunta (p. ej. en pruebas de construcción): no hay dónde mostrar el
            # diálogo, así que se confirma directo para no bloquear el flujo.
            _confirmar_de_verdad()

    def _build_controls() -> list[ft.Control]:
        _render_lineas()
        _render_pagos()
        _actualizar_boton_espera()
        controles: list[ft.Control] = [
            widgets.page_header("Punto de venta"),
            aviso_caja,
            ft.Row(
                controls=[
                    widgets.secondary_button("Aparcar venta", _aparcar_venta),
                    boton_ventas_espera,
                ],
                spacing=theme.SPACING["sm"],
            ),
            ft.Text("Cliente", weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    campo_cliente_busqueda,
                    widgets.secondary_button("Buscar", _buscar_cliente),
                ],
                spacing=theme.SPACING["sm"],
            ),
            resultados_cliente,
            cliente_elegido,
            ft.Divider(),
            ft.Text("Líneas", weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[campo_codigo_producto, campo_cantidad],
                wrap=True,
                spacing=theme.SPACING["sm"],
            ),
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
            widgets.primary_button("Confirmar venta", _confirmar),
        ]
        try:
            disponible_fiscal = fiscal.is_available(ctx.actor)
        except SistemasHNError:
            disponible_fiscal = False
        if disponible_fiscal:
            # La emisión fiscal real queda fuera de alcance de T4.6 (ver brief): se deja el
            # botón visible pero deshabilitado como referencia de que la función existe.
            boton_fiscal = widgets.secondary_button(
                "Emitir factura fiscal (pendiente de validación fiscal)", lambda e: None
            )
            boton_fiscal.disabled = True
            controles.append(boton_fiscal)
        return controles

    root.controls = _build_controls()
    return root
