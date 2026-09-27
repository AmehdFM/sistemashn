"""Fixtures compartidas para las pruebas de identidad (T1.2)."""

from datetime import timedelta

import pytest

from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.identity.service import IdentityService
from sistemashn.core.modules.contracts import ModuleDef, ModuleRegistry, PermissionDef, ProfileDef

PERMISO_VER = PermissionDef("core.usuarios.ver", "Ver usuarios", "Administración")
PERMISO_GESTIONAR = PermissionDef("core.usuarios.gestionar", "Gestionar usuarios", "Administración")
PERFIL_VENDEDOR = ProfileDef("vendedor", "Vendedor", frozenset({PERMISO_VER.code}))
PERFIL_ADMINISTRADOR = ProfileDef(
    "administrador",
    "Administrador",
    frozenset({PERMISO_VER.code, PERMISO_GESTIONAR.code}),
)


class MutableClock:
    """Reloj inyectable que se puede adelantar manualmente en las pruebas."""

    def __init__(self, initial):
        self._now = initial

    def __call__(self):
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


@pytest.fixture
def mutable_clock(now) -> MutableClock:
    return MutableClock(now)


@pytest.fixture
def registry() -> ModuleRegistry:
    reg = ModuleRegistry()
    reg.register(
        ModuleDef(
            code="core",
            label="Core",
            permissions=(PERMISO_VER, PERMISO_GESTIONAR),
            profiles=(PERFIL_VENDEDOR, PERFIL_ADMINISTRADOR),
        )
    )
    return reg


@pytest.fixture
def authorizer(registry, mutable_clock) -> Authorizer:
    return Authorizer(registry, clock=mutable_clock)


@pytest.fixture
def identity_service(session_factory, authorizer, mutable_clock) -> IdentityService:
    return IdentityService(session_factory, authorizer, clock=mutable_clock)
