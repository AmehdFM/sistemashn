"""Fixtures locales de las pruebas de compras (plan T3.2)."""

import pytest

from sistemashn.comercial.compras.service import PurchaseService
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.credito.service import AccountService


@pytest.fixture
def account_service(session_factory, authorizer, clock) -> AccountService:
    return AccountService(session_factory, authorizer, clock=clock)


@pytest.fixture
def purchase_service(
    session_factory, authorizer, clock, inventory_ledger, account_service
) -> PurchaseService:
    return PurchaseService(
        session_factory, authorizer, clock=clock, ledger=inventory_ledger, accounts=account_service
    )


@pytest.fixture
def proveedor_id(party_service, admin_actor) -> int:
    return party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.NEGOCIO, name="Repuestos El Motor", is_supplier=True),
    )
