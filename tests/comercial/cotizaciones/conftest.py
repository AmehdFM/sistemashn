"""Fixtures locales de las pruebas de cotizaciones (plan T4.1)."""

from decimal import Decimal

import pytest

from sistemashn.comercial.catalogo.kits import KitService
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.cotizaciones.service import QuoteService

from ..conftest import make_product_input


@pytest.fixture
def quote_service(session_factory, authorizer, clock, inventory_ledger) -> QuoteService:
    return QuoteService(session_factory, authorizer, clock=clock, ledger=inventory_ledger)


@pytest.fixture
def kit_service(session_factory, authorizer, clock) -> KitService:
    return KitService(session_factory, authorizer, clock=clock)


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
