"""Fixtures locales de las pruebas de reportes (plan T5.5)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from sistemashn.comercial.compras.schemas import PurchaseInput, PurchaseLineInput
from sistemashn.comercial.compras.service import PurchaseService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.reportes.service import ReportService
from sistemashn.comercial.ventas.models import Sale
from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
from sistemashn.comercial.ventas.service import SaleService

from ..compras.conftest import *  # noqa: F403 (reutiliza purchase_service, proveedor_id)
from ..ventas.conftest import *  # noqa: F403 (reutiliza sale_service, cliente_id, kits, etc.)


@pytest.fixture
def report_service(session_factory, authorizer, clock, inventory_service) -> ReportService:
    return ReportService(session_factory, authorizer, clock=clock, inventory=inventory_service)


@pytest.fixture
def report_service_sin_inventario(session_factory, authorizer, clock) -> ReportService:
    return ReportService(session_factory, authorizer, clock=clock)


def confirmar_compra(
    purchase_service: PurchaseService,
    actor,
    proveedor_id: int,
    producto_id: int,
    qty: str,
    unit_cost: str,
):
    """Confirma una compra al contado, para dejar costo histórico real en el inventario.

    Sin ISV explícito (tax_rate=0 en la línea) para que el pago exacto cubra el total sin crédito.
    """
    return purchase_service.confirm(
        actor,
        PurchaseInput(
            supplier_id=proveedor_id,
            lines=[
                PurchaseLineInput(
                    product_id=producto_id,
                    qty=Decimal(qty),
                    unit_cost=Decimal(unit_cost),
                    tax_rate=Decimal("0"),
                )
            ],
            payments=[
                PaymentInput(
                    method=PaymentMethod.EFECTIVO, amount=Decimal(qty) * Decimal(unit_cost)
                )
            ],
            request_id=uuid4().hex,
        ),
    )


def confirmar_venta(
    sale_service: SaleService,
    actor,
    producto_id: int,
    qty: str,
    unit_price: str,
    *,
    customer_id: int | None = None,
):
    """Confirma una venta de contado (tarjeta) sin caja, sin ISV explícito (tax_rate=0 en la
    línea) para que las pruebas comparen totales exactos sin depender de la tasa del producto."""
    total = Decimal(qty) * Decimal(unit_price)
    return sale_service.confirm(
        actor,
        SaleInput(
            customer_id=customer_id,
            lines=[
                SaleLineInput(
                    product_id=producto_id,
                    qty=Decimal(qty),
                    unit_price=Decimal(unit_price),
                    tax_rate=Decimal("0"),
                )
            ],
            payments=[PaymentInput(method=PaymentMethod.TARJETA, amount=total)],
            request_id=uuid4().hex,
        ),
    )


def anular_venta_directo(session_factory, sale_id: int) -> None:
    """Marca una venta como `anulada` directamente en el modelo.

    `SaleService.void` lo implementa otro agente en paralelo (T5.1); mientras no esté disponible,
    las pruebas de este paquete simulan el estado final sin depender de esa implementación.
    """
    with session_factory() as session:
        sale = session.get(Sale, sale_id)
        sale.status = "anulada"
        session.commit()


@pytest.fixture
def fecha_vencimiento() -> date:
    return date(2026, 12, 31)
