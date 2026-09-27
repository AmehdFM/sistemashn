"""Fixtures compartidas para las pruebas de ajustes (T1.5)."""

import pytest

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.modules.contracts import ModuleDef, ModuleRegistry, PermissionDef, ProfileDef
from sistemashn.core.settings.service import SettingsService

PERMISO_GESTIONAR = PermissionDef("core.ajustes.gestionar", "Gestionar ajustes", "Administración")
PERFIL_ADMINISTRADOR = ProfileDef(
    "administrador", "Administrador", frozenset({PERMISO_GESTIONAR.code})
)
PERFIL_VENDEDOR = ProfileDef("vendedor", "Vendedor", frozenset())


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(
        ModuleDef(
            code="core",
            label="Core",
            permissions=(PERMISO_GESTIONAR,),
            profiles=(PERFIL_ADMINISTRADOR, PERFIL_VENDEDOR),
        )
    )
    return reg


@pytest.fixture
def authorizer(registry, clock) -> Authorizer:
    return Authorizer(registry, clock=clock)


@pytest.fixture
def settings_service(session_factory, authorizer, clock, tmp_path) -> SettingsService:
    return SettingsService(session_factory, authorizer, clock, tmp_path / "data")


def actor_sin_permiso() -> Actor:
    return Actor(user_id=99, username="vendedor", is_admin=False, session_id="s1")
