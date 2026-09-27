"""Fixtures locales de las pruebas de ventas (plan T4.2)."""

from decimal import Decimal

import pytest

from sistemashn.comercial.caja.service import CashService
from sistemashn.comercial.catalogo.kits import KitService
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.cotizaciones.service import QuoteService
from sistemashn.comercial.credito.service import AccountService
from sistemashn.comercial.fiscal.service import FiscalService
from sistemashn.comercial.ventas.service import SaleService
from sistemashn.core.db.uow import run_in_transaction

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
def kit_service(session_factory, authorizer, clock) -> KitService:
    return KitService(session_factory, authorizer, clock=clock)


@pytest.fixture
def fiscal_service(session_factory, authorizer, clock) -> FiscalService:
    return FiscalService(session_factory, authorizer, clock=clock)


@pytest.fixture
def sale_service(
    session_factory,
    authorizer,
    clock,
    inventory_ledger,
    account_service,
    cash_service,
    quote_service,
    fiscal_service,
) -> SaleService:
    return SaleService(
        session_factory,
        authorizer,
        clock=clock,
        ledger=inventory_ledger,
        accounts=account_service,
        cash=cash_service,
        quotes=quote_service,
        fiscal=fiscal_service,
    )


@pytest.fixture
def cliente_id(party_service, admin_actor) -> int:
    return party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.PERSONA, name="Juan Pérez", is_customer=True),
    )


@pytest.fixture
def componente_a_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="PAD-A", name="Pastilla A"),
    )


@pytest.fixture
def componente_b_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="PAD-B", name="Pastilla B"),
    )


@pytest.fixture
def kit_id(
    catalog_service,
    kit_service,
    admin_actor,
    unidad_id,
    categoria_id,
    componente_a_id,
    componente_b_id,
) -> int:
    kit_id = catalog_service.create_product(
        admin_actor,
        make_product_input(
            unidad_id, categoria_id, code="KIT-1", name="Kit de frenos", is_kit=True
        ),
    )
    kit_service.set_components(
        admin_actor,
        kit_id,
        [(componente_a_id, Decimal("2")), (componente_b_id, Decimal("1"))],
    )
    return kit_id


def recibir_stock(
    session_factory, inventory_ledger, admin_actor, product_id, qty, unit_cost="50.00"
) -> None:
    """Da entrada a existencias directamente en el libro, sin pasar por compras."""

    def _op(session):
        inventory_ledger.receive(session, admin_actor, product_id, Decimal(qty), Decimal(unit_cost))

    run_in_transaction(session_factory, _op)
