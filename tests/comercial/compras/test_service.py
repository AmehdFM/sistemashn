"""Pruebas de `PurchaseService`: confirmación, crédito, precios y permisos (plan T3.2)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from tests.comercial.conftest import make_product_input

from sistemashn.comercial.catalogo.schemas import ProductInput
from sistemashn.comercial.compras.errors import InvalidPurchaseLine, PaymentsExceedTotal
from sistemashn.comercial.compras.models import Purchase
from sistemashn.comercial.compras.schemas import PurchaseInput, PurchaseLineInput
from sistemashn.comercial.credito.schemas import AccountKind
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.core.errors import PermissionDenied, ValidationError


def _input(
    supplier_id,
    lines,
    *,
    payments=None,
    credit_due_date=None,
    request_id="req-1",
    supplier_invoice_ref=None,
) -> PurchaseInput:
    return PurchaseInput(
        supplier_id=supplier_id,
        supplier_invoice_ref=supplier_invoice_ref,
        lines=lines,
        payments=payments or [],
        credit_due_date=credit_due_date,
        request_id=request_id,
    )


def _linea(product_id, qty="10", unit_cost="50.00", tax_rate=None) -> PurchaseLineInput:
    return PurchaseLineInput(
        product_id=product_id, qty=Decimal(qty), unit_cost=Decimal(unit_cost), tax_rate=tax_rate
    )


@pytest.fixture
def segundo_producto_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="FILTRO-1", name="Filtro de aceite"),
    )


def test_compra_al_contado_actualiza_costo_promedio(
    purchase_service, inventory_service, admin_actor, proveedor_id, producto_id, segundo_producto_id
):
    lineas = [
        _linea(producto_id, qty="10", unit_cost="50.00"),
        _linea(segundo_producto_id, qty="5", unit_cost="20.00"),
    ]
    total = Decimal("10") * Decimal("50.00") * Decimal("1.15") + Decimal("5") * Decimal(
        "20.00"
    ) * Decimal("1.15")
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=total)]

    vista = purchase_service.confirm(admin_actor, _input(proveedor_id, lineas, payments=pagos))

    assert vista.number == "C-000001"
    assert vista.credit_amount == Decimal("0.00")
    assert len(vista.lines) == 2

    stock = inventory_service.stock(admin_actor, producto_id)
    assert stock.avg_cost == Decimal("50.0000")


def test_compra_a_credito_crea_cuenta_por_pagar(
    purchase_service, account_service, admin_actor, proveedor_id, producto_id
):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    vista = purchase_service.confirm(
        admin_actor,
        _input(proveedor_id, lineas, credit_due_date=date(2026, 10, 15)),
    )

    esperado_total = Decimal("575.00")
    assert vista.total == esperado_total
    assert vista.credit_amount == esperado_total

    cuentas = account_service.list(admin_actor, AccountKind.PAYABLE)
    assert len(cuentas.items) == 1
    assert cuentas.items[0].original_amount == esperado_total
    assert cuentas.items[0].source_id == str(vista.id)


def test_pagos_mixtos_suman_total(purchase_service, admin_actor, proveedor_id, producto_id):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]  # total 575.00
    pagos = [
        PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("275.00")),
        PaymentInput(method=PaymentMethod.TARJETA, amount=Decimal("300.00")),
    ]
    vista = purchase_service.confirm(admin_actor, _input(proveedor_id, lineas, payments=pagos))

    assert vista.paid_initial == Decimal("575.00")
    assert vista.credit_amount == Decimal("0.00")
    assert len(vista.payments) == 2


def test_pagos_exceden_total_falla(purchase_service, admin_actor, proveedor_id, producto_id):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("600.00"))]

    with pytest.raises(PaymentsExceedTotal):
        purchase_service.confirm(admin_actor, _input(proveedor_id, lineas, payments=pagos))


def test_credito_sin_fecha_vencimiento_falla(
    purchase_service, admin_actor, proveedor_id, producto_id
):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    with pytest.raises(ValidationError):
        purchase_service.confirm(admin_actor, _input(proveedor_id, lineas))


def test_proveedor_inactivo_falla(
    purchase_service, party_service, admin_actor, proveedor_id, producto_id
):
    party_service.set_active(admin_actor, proveedor_id, False)
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))]
    with pytest.raises(ValidationError):
        purchase_service.confirm(admin_actor, _input(proveedor_id, lineas, payments=pagos))


def test_contraparte_no_proveedor_falla(purchase_service, party_service, admin_actor, producto_id):
    from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind

    cliente_id = party_service.create(
        admin_actor, PartyInput(kind=PartyKind.PERSONA, name="Juan Pérez", is_customer=True)
    )
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))]
    with pytest.raises(ValidationError):
        purchase_service.confirm(admin_actor, _input(cliente_id, lineas, payments=pagos))


def test_producto_kit_falla(
    purchase_service, catalog_service, admin_actor, proveedor_id, unidad_id, categoria_id
):
    kit_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="KIT-1",
            name="Kit de frenos",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("300.00"),
            min_stock=Decimal("0"),
            is_kit=True,
        ),
    )
    lineas = [_linea(kit_id, qty="1", unit_cost="100.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("115.00"))]
    with pytest.raises(InvalidPurchaseLine):
        purchase_service.confirm(admin_actor, _input(proveedor_id, lineas, payments=pagos))


def test_fallo_en_ultima_linea_no_deja_rastro(
    purchase_service,
    catalog_service,
    session_factory,
    admin_actor,
    proveedor_id,
    producto_id,
    unidad_id,
    categoria_id,
):
    kit_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="KIT-2",
            name="Kit de embrague",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("300.00"),
            min_stock=Decimal("0"),
            is_kit=True,
        ),
    )
    lineas = [
        _linea(producto_id, qty="10", unit_cost="50.00"),
        _linea(kit_id, qty="1", unit_cost="100.00"),
    ]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("690.00"))]

    with pytest.raises(InvalidPurchaseLine):
        purchase_service.confirm(admin_actor, _input(proveedor_id, lineas, payments=pagos))

    with session_factory() as session:
        assert session.scalars(select(Purchase)).all() == []

    stock = purchase_service_stock(session_factory, producto_id)
    assert stock == Decimal("0.000")


def purchase_service_stock(session_factory, product_id) -> Decimal:
    from sistemashn.comercial.inventario.models import Stock

    with session_factory() as session:
        stock = session.get(Stock, product_id)
        return stock.on_hand


def test_reintento_mismo_request_id_no_duplica(
    purchase_service, session_factory, admin_actor, proveedor_id, producto_id
):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))]
    data = _input(proveedor_id, lineas, payments=pagos, request_id="req-x")

    primero = purchase_service.confirm(admin_actor, data)
    segundo = purchase_service.confirm(admin_actor, data)

    assert primero.id == segundo.id
    assert primero.number == segundo.number == "C-000001"

    with session_factory() as session:
        assert len(session.scalars(select(Purchase)).all()) == 1


def test_historial_precios_conserva_ambas_compras(
    purchase_service, admin_actor, proveedor_id, producto_id
):
    purchase_service.confirm(
        admin_actor,
        _input(
            proveedor_id,
            [_linea(producto_id, qty="10", unit_cost="50.00")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))],
            request_id="req-1",
        ),
    )
    purchase_service.confirm(
        admin_actor,
        _input(
            proveedor_id,
            [_linea(producto_id, qty="5", unit_cost="60.00")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("345.00"))],
            request_id="req-2",
        ),
    )

    precios = purchase_service.last_prices(admin_actor, producto_id)
    assert [p.unit_cost for p in precios] == [Decimal("60.0000"), Decimal("50.0000")]


def test_vendedor_sin_permiso_no_puede_confirmar(
    purchase_service, vendedor_actor, proveedor_id, producto_id
):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))]
    with pytest.raises(PermissionDenied):
        purchase_service.confirm(vendedor_actor, _input(proveedor_id, lineas, payments=pagos))


def test_costos_ocultos_sin_permiso_com_costos_ver(
    purchase_service, bodega_actor, admin_actor, proveedor_id, producto_id
):
    lineas = [_linea(producto_id, qty="10", unit_cost="50.00")]
    pagos = [PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))]
    vista_admin = purchase_service.confirm(
        admin_actor, _input(proveedor_id, lineas, payments=pagos)
    )
    assert vista_admin.lines[0].unit_cost == Decimal("50.0000")

    # El perfil `bodega` tiene `com.compras.ver` pero no `com.costos.ver`.
    vista_bodega = purchase_service.get(bodega_actor, vista_admin.id)
    assert vista_bodega.lines[0].unit_cost is None

    with pytest.raises(PermissionDenied):
        purchase_service.last_prices(bodega_actor, producto_id)


def test_list_pagina_y_filtra_por_texto(
    purchase_service, party_service, admin_actor, proveedor_id, producto_id
):
    from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind

    otro_proveedor_id = party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.NEGOCIO, name="Refaccionaria Central", is_supplier=True),
    )
    purchase_service.confirm(
        admin_actor,
        _input(
            proveedor_id,
            [_linea(producto_id, qty="1", unit_cost="10.00")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("11.50"))],
            request_id="req-a",
        ),
    )
    purchase_service.confirm(
        admin_actor,
        _input(
            otro_proveedor_id,
            [_linea(producto_id, qty="1", unit_cost="10.00")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("11.50"))],
            request_id="req-b",
        ),
    )

    pagina = purchase_service.list(admin_actor, page=1, page_size=1)
    assert pagina.total == 2
    assert len(pagina.items) == 1

    filtradas = purchase_service.list(admin_actor, text="refaccionaria")
    assert filtradas.total == 1
    assert filtradas.items[0].supplier_id == otro_proveedor_id

    historial = purchase_service.supplier_history(admin_actor, proveedor_id)
    assert historial.total == 1
    assert historial.items[0].supplier_id == proveedor_id
