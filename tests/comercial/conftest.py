"""Fixtures compartidas para las pruebas de Comercial (catálogo T2.1 e inventario T2.2)."""

import pytest

from sistemashn.comercial.catalogo.schemas import CategoryInput, ProductInput, UnitInput
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.inventario.ledger import InventoryLedger
from sistemashn.comercial.inventario.service import InventoryService
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(CORE_MODULE)
    reg.register(COMERCIAL_MODULE)
    return reg


@pytest.fixture
def authorizer(registry, clock) -> Authorizer:
    return Authorizer(registry, clock=clock)


def _crear_usuario(session_factory, now, *, username, is_admin=False, profile_code=None) -> int:
    with session_factory() as session:
        user = User(
            username=username,
            full_name=f"Usuario {username}",
            password_hash="hash",
            is_admin=is_admin,
            is_active=True,
            profile_code=profile_code,
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        return user.id


@pytest.fixture
def admin_actor(session_factory, now) -> Actor:
    user_id = _crear_usuario(session_factory, now, username="admin1", is_admin=True)
    return Actor(user_id=user_id, username="admin1", is_admin=True, session_id="s-admin")


@pytest.fixture
def vendedor_actor(session_factory, now) -> Actor:
    user_id = _crear_usuario(session_factory, now, username="vendedor1", profile_code="vendedor")
    return Actor(user_id=user_id, username="vendedor1", is_admin=False, session_id="s-vendedor")


@pytest.fixture
def bodega_actor(session_factory, now) -> Actor:
    user_id = _crear_usuario(session_factory, now, username="bodega1", profile_code="bodega")
    return Actor(user_id=user_id, username="bodega1", is_admin=False, session_id="s-bodega")


@pytest.fixture
def catalog_service(session_factory, authorizer, clock) -> CatalogService:
    return CatalogService(session_factory, authorizer, clock=clock)


@pytest.fixture
def party_service(session_factory, authorizer, clock) -> PartyService:
    return PartyService(session_factory, authorizer, clock=clock)


@pytest.fixture
def inventory_ledger(clock) -> InventoryLedger:
    return InventoryLedger(clock=clock)


@pytest.fixture
def inventory_service(session_factory, authorizer, clock, inventory_ledger) -> InventoryService:
    return InventoryService(session_factory, authorizer, clock=clock, ledger=inventory_ledger)


@pytest.fixture
def unidad_id(catalog_service, admin_actor) -> int:
    return catalog_service.create_unit(
        admin_actor, UnitInput(code="UND", name="Unidad", allows_fraction=False)
    )


@pytest.fixture
def unidad_fraccion_id(catalog_service, admin_actor) -> int:
    return catalog_service.create_unit(
        admin_actor, UnitInput(code="LTS", name="Litros", allows_fraction=True)
    )


@pytest.fixture
def categoria_id(catalog_service, admin_actor) -> int:
    return catalog_service.create_category(admin_actor, CategoryInput(name="Frenos"))


def make_product_input(unidad_id, categoria_id=None, **overrides) -> ProductInput:
    data = {
        "code": "ABC-123",
        "name": "Pastillas de freno",
        "unit_id": unidad_id,
        "category_id": categoria_id,
        "tax_rate": "0.15",
        "sale_price": "150.00",
        "min_stock": "2",
    }
    data.update(overrides)
    return ProductInput(**data)


@pytest.fixture
def producto_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(admin_actor, make_product_input(unidad_id, categoria_id))


@pytest.fixture
def producto_fraccion_id(catalog_service, admin_actor, unidad_fraccion_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(
            unidad_fraccion_id, categoria_id, code="ACEITE-1", name="Aceite de motor"
        ),
    )
