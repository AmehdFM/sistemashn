"""Pantalla de devoluciones de cliente y a proveedor (cierre de Fase 5).

Decisión: `SaleLineView`/`PurchaseLineView` no exponen el `id` real de la línea (solo `line_no`,
ver `sistemashn.comercial.ventas.schemas`/`comercial.compras.schemas`), pero
`ReturnService.customer_return`/`supplier_return` requieren ese `id`. Como no está en el alcance
de esta tarea agregarlo a esos esquemas, esta pantalla resuelve `line_no` -> `id` con una lectura
directa de solo lectura (`session_scope`), igual que ya hace `components.tiene_permiso` para
verificar permisos: es una excepción puntual y documentada a "la UI solo llama servicios",
limitada a una consulta de solo lectura sin lógica de negocio.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import uuid4

import flet as ft
from sqlalchemy import select

from sistemashn.comercial.compras.models import PurchaseLine
from sistemashn.comercial.compras.schemas import PurchaseLineView, PurchaseSummary, PurchaseView
from sistemashn.comercial.compras.service import PurchaseService
from sistemashn.comercial.devoluciones.schemas import (
    CustomerReturnInput,
    CustomerReturnResolution,
    ReturnCondition,
    SupplierReturnInput,
    SupplierReturnResolution,
)
from sistemashn.comercial.devoluciones.service import ReturnService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ui.components import tiene_permiso
from sistemashn.comercial.ventas.models import SaleLine
from sistemashn.comercial.ventas.schemas import SaleLineView, SaleSummary, SaleView
from sistemashn.comercial.ventas.service import SaleService
from sistemashn.core.db.session import session_scope
from sistemashn.core.errors import SistemasHNError
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext

PERMISO = "com.devoluciones.gestionar"

_CONDICIONES = (
    (ReturnCondition.VENDIBLE, "Vendible"),
    (ReturnCondition.NO_VENDIBLE, "No vendible"),
)
_RESOLUCIONES_CLIENTE = (
    (CustomerReturnResolution.REEMBOLSO, "Reembolso"),
    (CustomerReturnResolution.CAMBIO, "Cambio"),
    (CustomerReturnResolution.SALDO_A_FAVOR, "Saldo a favor"),
)
_RESOLUCIONES_PROVEEDOR = (
    (SupplierReturnResolution.REEMPLAZO, "Reemplazo"),
    (SupplierReturnResolution.REEMBOLSO, "Reembolso"),
    (SupplierReturnResolution.CREDITO_FUTURO, "Crédito futuro"),
)


def _sale_line_id(ctx: AppContext, sale_id: int, line_no: int) -> int | None:
    with session_scope(ctx.session_factory, readonly=True) as session:
        return session.scalar(
            select(SaleLine.id).where(SaleLine.sale_id == sale_id, SaleLine.line_no == line_no)
        )


def _purchase_line_id(ctx: AppContext, purchase_id: int, line_no: int) -> int | None:
    with session_scope(ctx.session_factory, readonly=True) as session:
        return session.scalar(
            select(PurchaseLine.id).where(
                PurchaseLine.purchase_id == purchase_id, PurchaseLine.line_no == line_no
            )
        )


def build_returns_view(ctx: AppContext) -> ft.Control:
    if not tiene_permiso(ctx, PERMISO):
        return widgets.forbidden_view()

    modo = {"tipo": "cliente"}
    root = ft.Column(spacing=theme.SPACING["md"], expand=True, scroll=ft.ScrollMode.AUTO)

    def _mostrar(tipo: str) -> None:
        modo["tipo"] = tipo
        root.controls = _build_body()
        if root.page is not None:
            root.update()

    def _build_body() -> list[ft.Control]:
        selector = ft.Row(
            controls=[
                widgets.primary_button("Devolución de cliente", lambda e: _mostrar("cliente"))
                if modo["tipo"] != "cliente"
                else widgets.secondary_button("Devolución de cliente", lambda e: None),
                widgets.primary_button("Devolución a proveedor", lambda e: _mostrar("proveedor"))
                if modo["tipo"] != "proveedor"
                else widgets.secondary_button("Devolución a proveedor", lambda e: None),
            ],
            spacing=theme.SPACING["sm"],
        )
        cuerpo = (
            _build_customer_form(ctx) if modo["tipo"] == "cliente" else _build_supplier_form(ctx)
        )
        return [widgets.page_header("Devoluciones"), selector, ft.Divider(), cuerpo]

    root.controls = _build_body()
    return root


def _build_customer_form(ctx: AppContext) -> ft.Control:
    sales: SaleService = ctx.service("sales")
    returns: ReturnService = ctx.service("returns")

    estado: dict = {"venta": None, "linea": None, "request_id": uuid4().hex}

    campo_busqueda = widgets.form_field("Buscar venta por número")
    resultados = ft.Column(spacing=theme.SPACING["xs"])
    venta_info = ft.Text("", weight=ft.FontWeight.BOLD)
    lineas_col = ft.Column(spacing=theme.SPACING["xs"])
    linea_elegida = ft.Text("", color=theme.TEXT_MUTED)

    campo_cantidad = widgets.form_field("Cantidad a devolver")
    campo_condicion = ft.Dropdown(
        label="Condición",
        value=ReturnCondition.VENDIBLE.value,
        options=[ft.DropdownOption(key=c.value, text=t) for c, t in _CONDICIONES],
    )
    campo_resolucion = ft.Dropdown(
        label="Resolución",
        value=CustomerReturnResolution.REEMBOLSO.value,
        options=[ft.DropdownOption(key=r.value, text=t) for r, t in _RESOLUCIONES_CLIENTE],
    )
    campo_metodo_pago = ft.Dropdown(
        label="Método de pago",
        value=PaymentMethod.EFECTIVO.value,
        options=[ft.DropdownOption(key=m.value, text=m.value.capitalize()) for m in PaymentMethod],
    )
    campo_monto_pago = widgets.form_field("Monto del reembolso")
    campo_motivo = widgets.form_field("Motivo")
    error = ft.Text("", color=theme.ERROR)
    resultado = ft.Text("", color=theme.SUCCESS)

    def _buscar(_: ft.Event[ft.Control]) -> None:
        texto = (campo_busqueda.value or "").strip()
        if not texto:
            resultados.controls = []
            resultados.update()
            return
        try:
            pagina = sales.list(ctx.actor, text=texto, page=1, page_size=10)
        except SistemasHNError as exc:
            resultados.controls = [widgets.error_banner(str(exc))]
            resultados.update()
            return
        resultados.controls = [
            widgets.secondary_button(
                f"{r.number} · {widgets.format_lempiras(r.total)}",
                lambda e, resumen=r: _elegir_venta(resumen),
            )
            for r in pagina.items
        ]
        resultados.update()

    def _elegir_venta(resumen: SaleSummary) -> None:
        try:
            venta: SaleView = sales.get(ctx.actor, resumen.id)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        estado["venta"] = venta
        estado["linea"] = None
        venta_info.value = f"Venta {venta.number}"
        venta_info.update()
        _render_lineas(venta)
        resultados.controls = []
        resultados.update()

    def _render_lineas(venta: SaleView) -> None:
        lineas_col.controls = [
            widgets.secondary_button(
                f"Línea {li.line_no}: {li.description_snapshot} · cant {li.qty} · "
                f"{widgets.format_lempiras(li.unit_price)}",
                lambda e, ln=li: _elegir_linea(ln),
            )
            for li in venta.lines
            if li.kit_component_of is None
        ]
        lineas_col.update()

    def _elegir_linea(linea: SaleLineView) -> None:
        estado["linea"] = linea
        linea_elegida.value = f"Línea seleccionada: {linea.line_no} ({linea.description_snapshot})"
        linea_elegida.update()

    campo_busqueda.on_submit = _buscar

    def _registrar(_: ft.Event[ft.Control]) -> None:
        resultado.value = ""
        venta: SaleView | None = estado["venta"]
        linea: SaleLineView | None = estado["linea"]
        if venta is None or linea is None:
            error.value = "seleccione una venta y una línea"
            error.update()
            return
        line_id = _sale_line_id(ctx, venta.id, linea.line_no)
        if line_id is None:
            error.value = "no se pudo ubicar la línea seleccionada"
            error.update()
            return
        try:
            cantidad = Decimal((campo_cantidad.value or "").strip().replace(",", ""))
        except InvalidOperation:
            error.value = "cantidad inválida"
            error.update()
            return

        pago: PaymentInput | None = None
        resolucion = CustomerReturnResolution(campo_resolucion.value)
        if resolucion == CustomerReturnResolution.REEMBOLSO:
            try:
                monto_pago = Decimal((campo_monto_pago.value or "").strip().replace(",", ""))
            except InvalidOperation:
                error.value = "el monto del reembolso es inválido"
                error.update()
                return
            try:
                pago = PaymentInput(
                    method=PaymentMethod(campo_metodo_pago.value), amount=monto_pago
                )
            except Exception as exc:  # validación de Pydantic
                error.value = str(exc)
                error.update()
                return

        try:
            data = CustomerReturnInput(
                sale_line_id=line_id,
                qty=cantidad,
                condition=ReturnCondition(campo_condicion.value),
                resolution=resolucion,
                payment=pago,
                reason=(campo_motivo.value or "").strip() or None,
                request_id=estado["request_id"],
            )
        except Exception as exc:  # validación de Pydantic
            error.value = str(exc)
            error.update()
            return

        try:
            devolucion = returns.customer_return(ctx.actor, data)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return

        error.value = ""
        monto_txt = widgets.format_lempiras(devolucion.amount)
        resultado.value = (
            f"Devolución #{devolucion.id} registrada por {monto_txt} · "
            f"resolución: {devolucion.resolution}"
        )
        estado["request_id"] = uuid4().hex
        error.update()
        resultado.update()

    return ft.Column(
        controls=[
            ft.Row(
                controls=[campo_busqueda, widgets.secondary_button("Buscar", _buscar)],
                spacing=theme.SPACING["sm"],
            ),
            resultados,
            venta_info,
            lineas_col,
            linea_elegida,
            ft.Row(
                controls=[campo_cantidad, campo_condicion, campo_resolucion],
                wrap=True,
                spacing=theme.SPACING["sm"],
            ),
            ft.Row(
                controls=[campo_metodo_pago, campo_monto_pago],
                wrap=True,
                spacing=theme.SPACING["sm"],
            ),
            campo_motivo,
            error,
            resultado,
            widgets.primary_button("Registrar devolución", _registrar),
        ],
        spacing=theme.SPACING["sm"],
    )


def _build_supplier_form(ctx: AppContext) -> ft.Control:
    purchases: PurchaseService = ctx.service("purchases")
    returns: ReturnService = ctx.service("returns")

    estado: dict = {"compra": None, "linea": None, "request_id": uuid4().hex}

    campo_busqueda = widgets.form_field("Buscar compra por número")
    resultados = ft.Column(spacing=theme.SPACING["xs"])
    compra_info = ft.Text("", weight=ft.FontWeight.BOLD)
    lineas_col = ft.Column(spacing=theme.SPACING["xs"])
    linea_elegida = ft.Text("", color=theme.TEXT_MUTED)

    campo_cantidad = widgets.form_field("Cantidad a devolver")
    campo_resolucion = ft.Dropdown(
        label="Resolución",
        value=SupplierReturnResolution.REEMPLAZO.value,
        options=[ft.DropdownOption(key=r.value, text=t) for r, t in _RESOLUCIONES_PROVEEDOR],
    )
    campo_motivo = widgets.form_field("Motivo")
    error = ft.Text("", color=theme.ERROR)
    resultado = ft.Text("", color=theme.SUCCESS)

    def _buscar(_: ft.Event[ft.Control]) -> None:
        texto = (campo_busqueda.value or "").strip()
        if not texto:
            resultados.controls = []
            resultados.update()
            return
        try:
            pagina = purchases.list(ctx.actor, text=texto, page=1, page_size=10)
        except SistemasHNError as exc:
            resultados.controls = [widgets.error_banner(str(exc))]
            resultados.update()
            return
        resultados.controls = [
            widgets.secondary_button(
                f"{r.number} · {widgets.format_lempiras(r.total)}",
                lambda e, resumen=r: _elegir_compra(resumen),
            )
            for r in pagina.items
        ]
        resultados.update()

    def _elegir_compra(resumen: PurchaseSummary) -> None:
        try:
            compra: PurchaseView = purchases.get(ctx.actor, resumen.id)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return
        estado["compra"] = compra
        estado["linea"] = None
        compra_info.value = f"Compra {compra.number}"
        compra_info.update()
        _render_lineas(compra)
        resultados.controls = []
        resultados.update()

    def _render_lineas(compra: PurchaseView) -> None:
        lineas_col.controls = [
            widgets.secondary_button(
                f"Línea {li.line_no}: {li.description_snapshot} · cant {li.qty}",
                lambda e, ln=li: _elegir_linea(ln),
            )
            for li in compra.lines
        ]
        lineas_col.update()

    def _elegir_linea(linea: PurchaseLineView) -> None:
        estado["linea"] = linea
        linea_elegida.value = f"Línea seleccionada: {linea.line_no} ({linea.description_snapshot})"
        linea_elegida.update()

    campo_busqueda.on_submit = _buscar

    def _registrar(_: ft.Event[ft.Control]) -> None:
        resultado.value = ""
        compra: PurchaseView | None = estado["compra"]
        linea: PurchaseLineView | None = estado["linea"]
        if compra is None or linea is None:
            error.value = "seleccione una compra y una línea"
            error.update()
            return
        line_id = _purchase_line_id(ctx, compra.id, linea.line_no)
        if line_id is None:
            error.value = "no se pudo ubicar la línea seleccionada"
            error.update()
            return
        try:
            cantidad = Decimal((campo_cantidad.value or "").strip().replace(",", ""))
        except InvalidOperation:
            error.value = "cantidad inválida"
            error.update()
            return

        try:
            data = SupplierReturnInput(
                purchase_line_id=line_id,
                qty=cantidad,
                resolution=SupplierReturnResolution(campo_resolucion.value),
                reason=(campo_motivo.value or "").strip() or None,
                request_id=estado["request_id"],
            )
        except Exception as exc:  # validación de Pydantic
            error.value = str(exc)
            error.update()
            return

        try:
            devolucion = returns.supplier_return(ctx.actor, data)
        except SistemasHNError as exc:
            error.value = str(exc)
            error.update()
            return

        error.value = ""
        monto_txt = widgets.format_lempiras(devolucion.amount)
        resultado.value = (
            f"Devolución #{devolucion.id} registrada por {monto_txt} · "
            f"resolución: {devolucion.resolution}"
        )
        estado["request_id"] = uuid4().hex
        error.update()
        resultado.update()

    return ft.Column(
        controls=[
            ft.Row(
                controls=[campo_busqueda, widgets.secondary_button("Buscar", _buscar)],
                spacing=theme.SPACING["sm"],
            ),
            resultados,
            compra_info,
            lineas_col,
            linea_elegida,
            ft.Row(
                controls=[campo_cantidad, campo_resolucion],
                wrap=True,
                spacing=theme.SPACING["sm"],
            ),
            campo_motivo,
            error,
            resultado,
            widgets.primary_button("Registrar devolución", _registrar),
        ],
        spacing=theme.SPACING["sm"],
    )
