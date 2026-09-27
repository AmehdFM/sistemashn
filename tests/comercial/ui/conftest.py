"""Fixtures de las pruebas de pantallas de Comercial: registro, servicios y actores."""

from collections.abc import Callable

import pytest

from sistemashn.comercial.catalogo.excel import ExcelImportService
from sistemashn.comercial.catalogo.kits import KitService
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.inventario.service import InventoryService
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.core.ui.app_context import AppContext


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
def ctx_factory(
    session_factory, registry, authorizer, clock, tmp_path
) -> Callable[[Actor | None], AppContext]:
    def _build(actor: Actor | None) -> AppContext:
        catalog_service = CatalogService(session_factory, authorizer, clock=clock)
        inventory_service = InventoryService(session_factory, authorizer, clock=clock)
        kit_service = KitService(session_factory, authorizer, clock=clock)
        excel_service = ExcelImportService(
            session_factory, authorizer, clock=clock, catalog_service=catalog_service
        )
        services = {
            "catalog": catalog_service,
            "inventory": inventory_service,
            "kits": kit_service,
            "excel": excel_service,
        }
        return AppContext(
            session_factory=session_factory,
            registry=registry,
            authorizer=authorizer,
            services=services,
            clock=clock,
            data_dir=tmp_path,
            actor=actor,
            business_name="SistemasHN",
        )

    return _build


@pytest.fixture
def unidad_id(ctx_factory, admin_actor) -> int:
    from sistemashn.comercial.catalogo.schemas import UnitInput

    ctx = ctx_factory(admin_actor)
    catalog: CatalogService = ctx.service("catalog")
    return catalog.create_unit(
        admin_actor, UnitInput(code="UND", name="Unidad", allows_fraction=False)
    )


@pytest.fixture
def categoria_id(ctx_factory, admin_actor) -> int:
    from sistemashn.comercial.catalogo.schemas import CategoryInput

    ctx = ctx_factory(admin_actor)
    catalog: CatalogService = ctx.service("catalog")
    return catalog.create_category(admin_actor, CategoryInput(name="Frenos"))


@pytest.fixture
def producto_id(ctx_factory, admin_actor, unidad_id, categoria_id) -> int:
    from sistemashn.comercial.catalogo.schemas import ProductInput

    ctx = ctx_factory(admin_actor)
    catalog: CatalogService = ctx.service("catalog")
    return catalog.create_product(
        admin_actor,
        ProductInput(
            code="ABC-123",
            name="Pastillas de freno",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate="0.15",
            sale_price="150.00",
            min_stock="2",
        ),
    )


def contiene_texto(control, texto: str) -> bool:
    """Busca `texto` en un `ft.Text` o en el `content` de texto plano de un control."""
    import flet as ft

    if isinstance(control, ft.Text) and control.value == texto:
        return True
    contenido = getattr(control, "content", None)
    if isinstance(contenido, str) and contenido == texto:
        return True
    for atributo in ("controls", "content", "actions", "columns", "rows", "cells", "label"):
        valor = getattr(control, atributo, None)
        if valor is None:
            continue
        hijos = valor if isinstance(valor, list) else [valor]
        for hijo in hijos:
            if isinstance(hijo, ft.Control) and contiene_texto(hijo, texto):
                return True
    return False
