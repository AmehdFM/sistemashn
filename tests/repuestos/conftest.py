"""Fixtures compartidas para las pruebas de Repuestos (T2.4)."""

import pytest

from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.repuestos.module import REPUESTOS_MODULE
from sistemashn.repuestos.partes.search import RepuestosSearchProvider
from sistemashn.repuestos.partes.service import PartService
from sistemashn.repuestos.vehiculos.service import VehicleService


def make_product_input(unidad_id, categoria_id=None, **overrides):
    """Copiada de `tests/comercial/catalogo/conftest.py` (no se edita ese archivo)."""
    from sistemashn.comercial.catalogo.schemas import ProductInput

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
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(CORE_MODULE)
    reg.register(COMERCIAL_MODULE)
    reg.register(REPUESTOS_MODULE)
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
def bodega_repuestos_actor(session_factory, now) -> Actor:
    user_id = _crear_usuario(
        session_factory, now, username="bodega1", profile_code="repuestos_bodega"
    )
    return Actor(user_id=user_id, username="bodega1", is_admin=False, session_id="s-bodega")


@pytest.fixture
def catalog_service(session_factory, authorizer, clock) -> CatalogService:
    return CatalogService(
        session_factory, authorizer, clock=clock, search_providers=[RepuestosSearchProvider()]
    )


@pytest.fixture
def part_service(session_factory, authorizer, clock) -> PartService:
    return PartService(session_factory, authorizer, clock=clock)


@pytest.fixture
def vehicle_service(session_factory, authorizer, clock) -> VehicleService:
    return VehicleService(session_factory, authorizer, clock=clock)


@pytest.fixture
def unidad_id(catalog_service, admin_actor) -> int:
    from sistemashn.comercial.catalogo.schemas import UnitInput

    return catalog_service.create_unit(
        admin_actor, UnitInput(code="UND", name="Unidad", allows_fraction=False)
    )


@pytest.fixture
def categoria_id(catalog_service, admin_actor) -> int:
    from sistemashn.comercial.catalogo.schemas import CategoryInput

    return catalog_service.create_category(admin_actor, CategoryInput(name="Frenos"))


@pytest.fixture
def make_id(vehicle_service, admin_actor) -> int:
    return vehicle_service.create_make(admin_actor, "Toyota")


@pytest.fixture
def model_id(vehicle_service, admin_actor, make_id) -> int:
    return vehicle_service.create_model(admin_actor, make_id, "Corolla")
