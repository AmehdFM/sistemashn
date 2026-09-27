"""Fixtures locales de las pruebas de devoluciones (plan T5.2/T5.3)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from sistemashn.comercial.caja.service import CashService
from sistemashn.comercial.compras.models import PurchaseLine
from sistemashn.comercial.compras.schemas import PurchaseInput, PurchaseLineInput
from sistemashn.comercial.compras.service import PurchaseService
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.cotizaciones.service import QuoteService
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.devoluciones.service import ReturnService
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.comercial.ventas.models import SaleLine
from sistemashn.comercial.ventas.schemas import SaleInput, SaleLineInput
from sistemashn.comercial.ventas.service import SaleService
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.identity.models import User

from ..conftest import make_product_input


@pytest.fixture
def account_service(session_factory, authorizer, clock) -> AccountService:
    return AccountService(session_factory, authorizer, clock=clock)


@pytest.fixture
def cash_service(session_factory, authorizer, clock) -> CashService:
    return CashService(session_factory, authorizer, clock=clock)


@pytest.fixture
def quote_service(session_factory, authorizer, clock, inventory_ledger) -> QuoteService:
    return QuoteService(session_factory, authorizer, clock=clock, ledger=inventory_ledger)


@pytest.fixture
def purchase_service(
    session_factory, authorizer, clock, inventory_ledger, account_service
) -> PurchaseService:
    return PurchaseService(
        session_factory, authorizer, clock=clock, ledger=inventory_ledger, accounts=account_service
    )


@pytest.fixture
def sale_service(
    session_factory,
    authorizer,
    clock,
    inventory_ledger,
    account_service,
    cash_service,
    quote_service,
) -> SaleService:
    return SaleService(
        session_factory,
        authorizer,
        clock=clock,
        ledger=inventory_ledger,
        accounts=account_service,
        cash=cash_service,
        quotes=quote_service,
    )


@pytest.fixture
def return_service(
    session_factory, authorizer, clock, inventory_ledger, account_service
) -> ReturnService:
    return ReturnService(
        session_factory, authorizer, clock=clock, ledger=inventory_ledger, accounts=account_service
    )


@pytest.fixture
def proveedor_id(party_service, admin_actor) -> int:
    return party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.NEGOCIO, name="Repuestos El Motor", is_supplier=True),
    )


@pytest.fixture
def cliente_id(party_service, admin_actor) -> int:
    return party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.PERSONA, name="Juan Pérez", is_customer=True),
    )


@pytest.fixture
def producto_devolucion_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="DEV-1", name="Filtro de aceite"),
    )


@pytest.fixture
def compra_confirmada(purchase_service, admin_actor, proveedor_id, producto_devolucion_id):
    """Una compra confirmada de 10 unidades a Lps 50.00, pagada de contado."""
    return purchase_service.confirm(
        admin_actor,
        PurchaseInput(
            supplier_id=proveedor_id,
            lines=[
                PurchaseLineInput(
                    product_id=producto_devolucion_id, qty=Decimal("10"), unit_cost=Decimal("50.00")
                )
            ],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("575.00"))],
            request_id="compra-devoluciones-1",
        ),
    )


@pytest.fixture
def compra_a_credito(purchase_service, admin_actor, proveedor_id, producto_devolucion_id):
    """Compra a crédito completo de 10 unidades, para probar `credito_futuro`."""
    return purchase_service.confirm(
        admin_actor,
        PurchaseInput(
            supplier_id=proveedor_id,
            lines=[
                PurchaseLineInput(
                    product_id=producto_devolucion_id, qty=Decimal("10"), unit_cost=Decimal("50.00")
                )
            ],
            payments=[],
            credit_due_date="2027-01-01",
            request_id="compra-devoluciones-credito-1",
        ),
    )


@pytest.fixture
def venta_confirmada(
    sale_service, admin_actor, cliente_id, producto_devolucion_id, compra_confirmada
):
    """Una venta confirmada de 5 unidades a contado (requiere existencias ya recibidas)."""
    return sale_service.confirm(
        admin_actor,
        SaleInput(
            customer_id=cliente_id,
            lines=[SaleLineInput(product_id=producto_devolucion_id, qty=Decimal("5"))],
            payments=[PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("862.50"))],
            request_id="venta-devoluciones-1",
        ),
    )


@pytest.fixture
def sale_line_id(session_factory, venta_confirmada) -> int:
    """El id real de `com_sale_line` de la única línea de `venta_confirmada`."""
    with session_factory() as session:
        return session.scalars(
            select(SaleLine.id).where(SaleLine.sale_id == venta_confirmada.id)
        ).one()


@pytest.fixture
def purchase_line_id(session_factory, compra_confirmada) -> int:
    """El id real de `com_purchase_line` de la única línea de `compra_confirmada`."""
    with session_factory() as session:
        return session.scalars(
            select(PurchaseLine.id).where(PurchaseLine.purchase_id == compra_confirmada.id)
        ).one()


@pytest.fixture
def purchase_line_id_credito(session_factory, compra_a_credito) -> int:
    """El id real de `com_purchase_line` de la única línea de `compra_a_credito`."""
    with session_factory() as session:
        return session.scalars(
            select(PurchaseLine.id).where(PurchaseLine.purchase_id == compra_a_credito.id)
        ).one()


@pytest.fixture
def sin_permiso_actor(session_factory, now) -> Actor:
    """Usuario activo sin perfil ni overrides: no tiene `com.devoluciones.gestionar`."""
    with session_factory() as session:
        user = User(
            username="sin_permiso",
            full_name="Usuario sin permiso",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            profile_code=None,
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        user_id = user.id
    return Actor(user_id=user_id, username="sin_permiso", is_admin=False, session_id="s-sp")
