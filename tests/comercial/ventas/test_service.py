"""Pruebas de `SaleService`: confirmación, kits, pagos mixtos, crédito y conversión (plan T4.2)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from tests.comercial.conftest import make_product_input

from sistemashn.comercial.caja.errors import NoCashSessionOpen
from sistemashn.comercial.cotizaciones.schemas import QuoteInput, QuoteLineInput
from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.fiscal.schemas import FiscalAuthorizationInput
from sistemashn.comercial.inventario.errors import InsufficientStock
from sistemashn.comercial.inventario.models import Stock
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ventas.errors import PaymentsMismatch, QuoteConversionMismatch
from sistemashn.comercial.ventas.models import Sale
from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
from sistemashn.core.errors import PermissionDenied, ValidationError

from ..fiscal.conftest import set_business_fiscal
from .conftest import recibir_stock


def _input(
    lines,
    *,
    customer_id=None,
    quote_id=None,
    payments=None,
    credit_due_date=None,
    cash_session_id=None,
    accept_changes=False,
    request_id="req-1",
) -> SaleInput:
    return SaleInput(
        customer_id=customer_id,
        quote_id=quote_id,
        lines=lines,
        payments=payments or [],
        credit_due_date=credit_due_date,
        cash_session_id=cash_session_id,
        accept_changes=accept_changes,
        request_id=request_id,
    )


def _linea(product_id, qty="1", unit_price=None) -> SaleLineInput:
    return SaleLineInput(product_id=product_id, qty=Decimal(qty), unit_price=unit_price)


def _stock(session_factory, product_id) -> Stock:
    with session_factory() as session:
        return session.get(Stock, product_id)


def test_venta_simple_al_contado(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")

    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(
        admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos)
    )

    assert vista.number == "V-000001"
    assert vista.total == Decimal("172.50")
    assert vista.change_amount == Decimal("0.00")
    assert vista.credit_amount == Decimal("0.00")
    assert len(vista.lines) == 1

    stock = _stock(session_factory, producto_id)
    assert stock.on_hand == Decimal("9.000")


def test_venta_de_kit_genera_lineas_de_componente_y_descuenta_inventario(
    sale_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, componente_a_id, "10", "20.00")
    recibir_stock(session_factory, inventory_ledger, admin_actor, componente_b_id, "10", "30.00")

    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(admin_actor, _input([_linea(kit_id, qty="1")], payments=pagos))

    # Una línea encabezado del kit + una línea por cada componente.
    assert len(vista.lines) == 3
    encabezado = next(li for li in vista.lines if li.product_id == kit_id)
    componentes = [li for li in vista.lines if li.kit_component_of == encabezado.line_no]
    assert len(componentes) == 2
    assert encabezado.unit_cost_snapshot == Decimal("70.0000")  # 2*20 + 1*30

    stock_a = _stock(session_factory, componente_a_id)
    stock_b = _stock(session_factory, componente_b_id)
    assert stock_a.on_hand == Decimal("8.000")  # 10 - 2*1
    assert stock_b.on_hand == Decimal("9.000")  # 10 - 1*1


def test_pagos_mixtos_vuelto_solo_por_excedente_de_efectivo(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    # total = 172.50; se paga 150 tarjeta + 50 efectivo = 200, exceso 27.50, todo cubierto por
    # el efectivo (50 > 27.50).
    pagos = [
        PaymentInput(method=PaymentMethod.TARJETA, amount=Decimal("150.00")),
        PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("50.00")),
    ]
    vista = sale_service.confirm(
        admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos)
    )

    assert vista.paid_amount == Decimal("200.00")
    assert vista.change_amount == Decimal("27.50")
    assert vista.credit_amount == Decimal("0.00")


def test_pagos_exceden_total_sin_efectivo_falla(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.TARJETA, amount=Decimal("200.00"))]
    with pytest.raises(PaymentsMismatch):
        sale_service.confirm(admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos))


def test_venta_a_credito_sin_cliente_falla(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    with pytest.raises(ValidationError):
        sale_service.confirm(
            admin_actor,
            _input([_linea(producto_id, qty="1")], credit_due_date=date(2026, 10, 15)),
        )


def test_venta_a_credito_con_cliente_crea_cxc(
    sale_service,
    account_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    cliente_id,
    producto_id,
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    vista = sale_service.confirm(
        admin_actor,
        _input(
            [_linea(producto_id, qty="1")],
            customer_id=cliente_id,
            credit_due_date=date(2026, 10, 15),
        ),
    )

    assert vista.credit_amount == Decimal("172.50")
    cuentas = account_service.list(admin_actor, AccountKind.RECEIVABLE)
    assert len(cuentas.items) == 1
    assert cuentas.items[0].original_amount == Decimal("172.50")
    assert cuentas.items[0].source_id == str(vista.id)

    # Un abono la va saldando.
    account_service.pay(
        admin_actor,
        cuentas.items[0].id,
        PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("100.00")),
        request_id="abono-1",
    )
    saldo = account_service.get(admin_actor, cuentas.items[0].id)
    assert saldo.balance == Decimal("72.50")


def test_conversion_de_cotizacion_con_apartado_consume_apartado_y_marca_convertida(
    sale_service,
    quote_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    cliente_id,
    producto_id,
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    cotizacion = quote_service.create(
        admin_actor,
        QuoteInput(
            customer_id=cliente_id,
            lines=[QuoteLineInput(product_id=producto_id, qty=Decimal("3"))],
            valid_until=date(2026, 12, 31),
            reserve=True,
            request_id="cot-1",
        ),
    )

    vista = sale_service.confirm(
        admin_actor,
        _input(
            [_linea(producto_id, qty="3")],
            customer_id=cliente_id,
            quote_id=cotizacion.id,
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("517.50"))],
        ),
    )

    assert vista.total == Decimal("517.50")
    stock = _stock(session_factory, producto_id)
    # 10 recibidas, 3 reservadas y luego emitidas desde el apartado: on_hand baja 3, reserved a 0.
    assert stock.on_hand == Decimal("7.000")
    assert stock.reserved == Decimal("0.000")

    cotizacion_actualizada = quote_service.get(admin_actor, cotizacion.id)
    assert cotizacion_actualizada.status == "convertida"


def test_conversion_con_cambio_de_precio_se_detiene_sin_accept_changes(
    sale_service,
    quote_service,
    catalog_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    cliente_id,
    producto_id,
    unidad_id,
    categoria_id,
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    cotizacion = quote_service.create(
        admin_actor,
        QuoteInput(
            customer_id=cliente_id,
            lines=[QuoteLineInput(product_id=producto_id, qty=Decimal("2"))],
            valid_until=date(2026, 12, 31),
            reserve=False,
            request_id="cot-2",
        ),
    )

    catalog_service.update_product(
        admin_actor,
        producto_id,
        make_product_input(unidad_id, categoria_id, sale_price=Decimal("200.00")),
    )

    data = _input(
        [_linea(producto_id, qty="2", unit_price=Decimal("200.00"))],
        customer_id=cliente_id,
        quote_id=cotizacion.id,
        payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("460.00"))],
    )

    with pytest.raises(QuoteConversionMismatch):
        sale_service.confirm(admin_actor, data)

    data_aceptada = _input(
        [_linea(producto_id, qty="2", unit_price=Decimal("200.00"))],
        customer_id=cliente_id,
        quote_id=cotizacion.id,
        payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("460.00"))],
        accept_changes=True,
        request_id="req-aceptado",
    )
    vista = sale_service.confirm(admin_actor, data_aceptada)
    assert vista.total == Decimal("460.00")


def test_kit_sin_stock_suficiente_en_componente_falla_sin_dejar_rastro(
    sale_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, componente_a_id, "1", "20.00")
    recibir_stock(session_factory, inventory_ledger, admin_actor, componente_b_id, "10", "30.00")

    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]

    with pytest.raises(InsufficientStock):
        sale_service.confirm(admin_actor, _input([_linea(kit_id, qty="1")], payments=pagos))

    with session_factory() as session:
        assert session.scalars(select(Sale)).all() == []

    stock_a = _stock(session_factory, componente_a_id)
    stock_b = _stock(session_factory, componente_b_id)
    assert stock_a.on_hand == Decimal("1.000")
    assert stock_b.on_hand == Decimal("10.000")


def test_reintento_mismo_request_id_no_duplica(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    data = _input([_linea(producto_id, qty="1")], payments=pagos, request_id="req-x")

    primero = sale_service.confirm(admin_actor, data)
    segundo = sale_service.confirm(admin_actor, data)

    assert primero.id == segundo.id
    assert primero.number == segundo.number == "V-000001"

    with session_factory() as session:
        assert len(session.scalars(select(Sale)).all()) == 1


def test_sin_permiso_no_puede_confirmar(
    sale_service, session_factory, inventory_ledger, admin_actor, bodega_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    with pytest.raises(PermissionDenied):
        sale_service.confirm(bodega_actor, _input([_linea(producto_id, qty="1")], payments=pagos))


# -- Anulación (T5.1) ---------------------------------------------------------


def test_anular_venta_al_contado_revierte_stock(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(
        admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos)
    )
    assert _stock(session_factory, producto_id).on_hand == Decimal("9.000")

    anulada = sale_service.void(admin_actor, vista.id, "cliente se arrepintió")

    assert anulada.status == "anulada"
    assert _stock(session_factory, producto_id).on_hand == Decimal("10.000")


def test_anular_venta_a_credito_salda_cxc(
    sale_service,
    account_service,
    session_factory,
    inventory_ledger,
    admin_actor,
    cliente_id,
    producto_id,
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    vista = sale_service.confirm(
        admin_actor,
        _input(
            [_linea(producto_id, qty="1")],
            customer_id=cliente_id,
            credit_due_date=date(2026, 10, 15),
        ),
    )
    cuentas = account_service.list(admin_actor, AccountKind.RECEIVABLE)
    cuenta_id = cuentas.items[0].id
    assert account_service.get(admin_actor, cuenta_id).balance == Decimal("172.50")

    sale_service.void(admin_actor, vista.id, "error de captura")

    assert account_service.get(admin_actor, cuenta_id).balance == Decimal("0.00")


def test_anular_venta_con_factura_fiscal_falla(
    sale_service, fiscal_service, session_factory, now, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(
        admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos)
    )

    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    fiscal_service.register_authorization(
        admin_actor,
        FiscalAuthorizationInput(
            cai="A1B2C3-A1B2C3-A1B2C3-A1B2C3-A1B2C3",
            range_start="001-001-01-00000001",
            range_end="001-001-01-00000100",
            valid_until=date(2030, 1, 1),
        ),
    )
    fiscal_service.issue(admin_actor, sale_id=vista.id, snapshot={"total": str(vista.total)})

    with pytest.raises(ValidationError):
        sale_service.void(admin_actor, vista.id, "no se debe poder")


def test_anular_dos_veces_falla(
    sale_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(
        admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos)
    )
    sale_service.void(admin_actor, vista.id, "primera anulación")

    with pytest.raises(ValidationError):
        sale_service.void(admin_actor, vista.id, "segunda anulación")


def test_anular_venta_sin_permiso_falla(
    sale_service, session_factory, inventory_ledger, admin_actor, vendedor_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(
        admin_actor, _input([_linea(producto_id, qty="1")], payments=pagos)
    )

    with pytest.raises(PermissionDenied):
        sale_service.void(vendedor_actor, vista.id, "sin permiso")


def test_anular_venta_con_caja_ya_cerrada_falla(
    sale_service, cash_service, session_factory, inventory_ledger, admin_actor, producto_id
):
    recibir_stock(session_factory, inventory_ledger, admin_actor, producto_id, "10")
    sesion = cash_service.open(admin_actor, Decimal("100.00"))
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("172.50"))]
    vista = sale_service.confirm(
        admin_actor,
        _input([_linea(producto_id, qty="1")], payments=pagos, cash_session_id=sesion.id),
    )
    cash_service.close(admin_actor, Decimal("272.50"))

    with pytest.raises(NoCashSessionOpen):
        sale_service.void(admin_actor, vista.id, "la caja ya cerró")

    # No debió tocar el inventario: se valida la caja antes de revertir cualquier cosa.
    assert _stock(session_factory, producto_id).on_hand == Decimal("9.000")
