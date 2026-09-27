"""Fixtures compartidas de las pruebas de vistas del Core: registro, servicios y actores."""

from collections.abc import Callable

import pytest

from sistemashn.core.audit.service import AuditQueryService
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer, PermissionAdminService
from sistemashn.core.identity.models import User
from sistemashn.core.identity.passwords import hash_password
from sistemashn.core.identity.recovery import RecoveryService
from sistemashn.core.identity.service import IdentityService
from sistemashn.core.licensing.service import LicenseService
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.core.settings.service import SettingsService
from sistemashn.core.ui.app_context import AppContext


@pytest.fixture
def registry() -> ModuleRegistry:
    registro = ModuleRegistry()
    registro.register(CORE_MODULE)
    return registro


@pytest.fixture
def authorizer(registry, clock) -> Authorizer:
    return Authorizer(registry, clock=clock)


def _crear_usuario(session_factory, now, *, username: str, is_admin: bool) -> int:
    with session_factory() as session:
        user = User(
            username=username,
            full_name=username.capitalize(),
            password_hash=hash_password("clave-de-prueba-1"),
            is_admin=is_admin,
            is_active=True,
            profile_code="administrador" if is_admin else None,
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
def admin_user_id(session_factory, now) -> int:
    return _crear_usuario(session_factory, now, username="admin", is_admin=True)


@pytest.fixture
def admin_actor(admin_user_id) -> Actor:
    return Actor(user_id=admin_user_id, username="admin", is_admin=True, session_id="s-admin")


@pytest.fixture
def limited_user_id(session_factory, now, admin_user_id) -> int:
    return _crear_usuario(session_factory, now, username="vendedor", is_admin=False)


@pytest.fixture
def limited_actor(limited_user_id) -> Actor:
    return Actor(
        user_id=limited_user_id, username="vendedor", is_admin=False, session_id="s-vendedor"
    )


@pytest.fixture
def ctx_factory(
    session_factory, registry, authorizer, clock, tmp_path
) -> Callable[[Actor | None], AppContext]:
    def _build(actor: Actor | None) -> AppContext:
        services = {
            "identity": IdentityService(session_factory, authorizer, clock=clock),
            "permissions": PermissionAdminService(session_factory, authorizer, clock),
            "audit": AuditQueryService(session_factory, authorizer),
            "settings": SettingsService(session_factory, authorizer, clock, tmp_path),
            "license": LicenseService(session_factory, {}, clock=clock),
            "recovery": RecoveryService(session_factory, clock, {}, lambda: "instalacion-test"),
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


def contiene_texto(control, texto: str) -> bool:
    """Busca `texto` en un `ft.Text` o en el `content` de texto plano de un control (botones)."""
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
