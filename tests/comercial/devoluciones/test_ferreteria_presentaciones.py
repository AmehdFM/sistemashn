"""Compra y venta reales desde presentaciones de Ferretería."""

from datetime import date
from decimal import Decimal

import pytest

from sistemashn.comercial.catalogo.schemas import ProductInput
from sistemashn.comercial.compras.schemas import PurchaseInput
from sistemashn.comercial.cotizaciones.schemas import QuoteInput
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.errors import NotFound, ValidationError
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.ferreteria.catalogo.service import FerreteriaCatalogService
from sistemashn.ferreteria.module import FERRETERIA_MODULE
from sistemashn.ferreteria.operaciones import FerreteriaLineBuilder


@pytest.fixture
def fer_lines(session_factory, clock):
    registry = ModuleRegistry()
    registry.register(CORE_MODULE)
    registry.register(COMERCIAL_MODULE)
    registry.register(FERRETERIA_MODULE)
    authorizer = Authorizer(registry, clock=clock)
    catalog = FerreteriaCatalogService(session_factory, authorizer, clock)
    return catalog, FerreteriaLineBuilder(catalog, session_factory)


def test_dos_cajas_compradas_tres_piezas_vendidas(
    fer_lines,
    catalog_service,
    purchase_service,
    sale_service,
    quote_service,
    inventory_service,
    admin_actor,
    proveedor_id,
    unidad_id,
):
    catalog, lines = fer_lines
    product_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="TOR-M8-30",
            name="Tornillo M8 × 30",
            unit_id=unidad_id,
            tax_rate="0",
            sale_price="0.80",
            min_stock="0",
        ),
    )
    pack_id = catalog.create_pack(
        admin_actor,
        product_id,
        code="CAJA-100-M8",
        label="Caja de 100",
        factor_base="100",
        permits_fraction=False,
        price="80.00",
    )
    purchase = purchase_service.confirm(
        admin_actor,
        PurchaseInput(
            supplier_id=proveedor_id,
            lines=[lines.purchase_line(admin_actor, pack_id, "2", "50.00")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("100"))],
            request_id="fer-2-cajas",
        ),
    )
    assert inventory_service.stock(admin_actor, product_id).on_hand == Decimal("200")
    assert purchase.lines[0].presentation.label == "Caja de 100"
    assert purchase.lines[0].presentation.quantity == Decimal("2")
    assert purchase.lines[0].presentation.factor_base == Decimal("100")
    assert (
        purchase_service.confirm(
            admin_actor,
            PurchaseInput(
                supplier_id=proveedor_id,
                lines=[lines.purchase_line(admin_actor, pack_id, "2", "50.00")],
                payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("100"))],
                request_id="fer-2-cajas",
            ),
        ).id
        == purchase.id
    )
    assert inventory_service.stock(admin_actor, product_id).on_hand == Decimal("200")

    sale = sale_service.confirm(
        admin_actor,
        SaleInput(
            lines=[SaleLineInput(product_id=product_id, qty="3")],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("2.40"))],
            request_id="fer-3-piezas",
        ),
    )
    assert sale.lines[0].qty == Decimal("3")
    assert inventory_service.stock(admin_actor, product_id).on_hand == Decimal("197")

    box_line = lines.sale_line(admin_actor, pack_id, "1")
    assert box_line.qty == Decimal("100")
    assert box_line.presentation.unit_amount == Decimal("80.00")
    assert box_line.unit_price == Decimal("0.80")
    quote = quote_service.create(
        admin_actor,
        QuoteInput(
            lines=[lines.quote_line(admin_actor, pack_id, "1")],
            valid_until=date(2026, 10, 15),
            reserve=True,
            request_id="fer-caja-cotizada",
        ),
    )
    assert quote.lines[0].presentation.label == "Caja de 100"
    assert inventory_service.stock(admin_actor, product_id).reserved == Decimal("100")
    box_sale = sale_service.confirm(
        admin_actor,
        SaleInput(
            quote_id=quote.id,
            lines=[box_line],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("80"))],
            request_id="fer-caja-vendida",
        ),
    )
    assert box_sale.lines[0].presentation.label == "Caja de 100"
    assert box_sale.lines[0].presentation.factor_base == Decimal("100")
    assert box_sale.lines[0].qty == Decimal("100")
    assert inventory_service.stock(admin_actor, product_id).on_hand == Decimal("97")
    again = sale_service.confirm(
        admin_actor,
        SaleInput(
            quote_id=quote.id,
            lines=[box_line],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("80"))],
            request_id="fer-caja-vendida",
        ),
    )
    assert again.id == box_sale.id
    assert inventory_service.stock(admin_actor, product_id).on_hand == Decimal("97")
    catalog.set_pack_active(admin_actor, pack_id, False)
    assert catalog.resolve_barcode(admin_actor, "CAJA-100-M8") is None
    assert (
        purchase_service.get(admin_actor, purchase.id).lines[0].presentation.label == "Caja de 100"
    )
    assert sale_service.get(admin_actor, box_sale.id).lines[0].presentation.label == "Caja de 100"
    with pytest.raises(NotFound):
        lines.sale_line(admin_actor, pack_id, "1")


def test_rechaza_costo_que_no_puede_convertirse_sin_redondeo(
    fer_lines, catalog_service, admin_actor, unidad_id
):
    catalog, lines = fer_lines
    product_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="CLAVO-3",
            name="Clavo 3",
            unit_id=unidad_id,
            tax_rate="0",
            sale_price="1",
            min_stock="0",
        ),
    )
    pack_id = catalog.create_pack(
        admin_actor,
        product_id,
        code=None,
        label="Bolsa de 3",
        factor_base="3",
        permits_fraction=False,
    )
    with pytest.raises(ValidationError, match="exactamente"):
        lines.purchase_line(admin_actor, pack_id, "1", "1.00")
