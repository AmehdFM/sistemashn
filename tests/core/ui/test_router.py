"""Pruebas de Router: menú visible por actor y resolución de rutas (T1.6a)."""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft
import pytest

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.modules.contracts import ScreenDef
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.router import Router

RUTA_LIBRE = ScreenDef(
    route="/libre", label="Libre", icon="HOME", permission=None, group="General", order=1
)
RUTA_PERMITIDA = ScreenDef(
    route="/permitida",
    label="Permitida",
    icon="CHECK",
    permission="core.permitido",
    group="Administración",
    order=1,
)
RUTA_DENEGADA = ScreenDef(
    route="/denegada",
    label="Denegada",
    icon="LOCK",
    permission="core.denegado",
    group="Administración",
    order=2,
)


@dataclass
class FakeRegistry:
    """Registro falso: expone solo `screens()`, como exige el Router."""

    pantallas: list[ScreenDef]

    def screens(self) -> list[ScreenDef]:
        return list(self.pantallas)


class FakeAuthorizer:
    """Authorizer falso: `can` según un conjunto fijo de permisos concedidos."""

    def __init__(self, permisos_concedidos: set[str]) -> None:
        self.permisos_concedidos = permisos_concedidos

    def can(self, session, actor, code: str) -> bool:
        return code in self.permisos_concedidos


ACTOR = Actor(user_id=1, username="ana", is_admin=False, session_id="s1")


def _builder(route: str):
    def _build(ctx: AppContext) -> ft.Control:
        return ft.Text(f"pantalla {route}")

    return _build


@pytest.fixture
def registry() -> FakeRegistry:
    return FakeRegistry([RUTA_DENEGADA, RUTA_LIBRE, RUTA_PERMITIDA])


@pytest.fixture
def authorizer() -> FakeAuthorizer:
    return FakeAuthorizer({"core.permitido"})


@pytest.fixture
def builders() -> dict[str, object]:
    return {
        RUTA_LIBRE.route: _builder(RUTA_LIBRE.route),
        RUTA_PERMITIDA.route: _builder(RUTA_PERMITIDA.route),
        RUTA_DENEGADA.route: _builder(RUTA_DENEGADA.route),
    }


def _ctx(session_factory, registry, authorizer, *, actor: Actor | None) -> AppContext:
    return AppContext(
        session_factory=session_factory,
        registry=registry,
        authorizer=authorizer,
        actor=actor,
    )


def test_visible_screens_sin_actor_es_vacio(session_factory, registry, authorizer, builders):
    ctx = _ctx(session_factory, registry, authorizer, actor=None)
    router = Router(ctx, builders)
    assert router.visible_screens() == []


def test_visible_screens_con_actor_filtra_y_ordena(session_factory, registry, authorizer, builders):
    ctx = _ctx(session_factory, registry, authorizer, actor=ACTOR)
    router = Router(ctx, builders)

    visibles = router.visible_screens()

    # Orden por (group, order): "Administración" precede a "General" alfabéticamente.
    assert [s.route for s in visibles] == [RUTA_PERMITIDA.route, RUTA_LIBRE.route]


def test_visible_screens_requiere_builder_registrado(session_factory, registry, authorizer):
    ctx = _ctx(session_factory, registry, authorizer, actor=ACTOR)
    router = Router(ctx, {RUTA_LIBRE.route: _builder(RUTA_LIBRE.route)})

    visibles = router.visible_screens()

    assert [s.route for s in visibles] == [RUTA_LIBRE.route]


def test_resolve_ruta_prohibida_es_forbidden_aunque_no_este_en_el_menu(
    session_factory, registry, authorizer, builders
):
    ctx = _ctx(session_factory, registry, authorizer, actor=ACTOR)
    router = Router(ctx, builders)

    # RUTA_DENEGADA no aparece en visible_screens(), pero resolve() vuelve a verificar.
    assert RUTA_DENEGADA.route not in [s.route for s in router.visible_screens()]
    resultado = router.resolve(RUTA_DENEGADA.route)

    assert resultado.kind == "forbidden"
    assert resultado.screen == RUTA_DENEGADA


def test_resolve_ruta_inexistente_es_not_found(session_factory, registry, authorizer, builders):
    ctx = _ctx(session_factory, registry, authorizer, actor=ACTOR)
    router = Router(ctx, builders)

    resultado = router.resolve("/no-existe")

    assert resultado.kind == "not_found"
    assert resultado.screen is None


def test_resolve_sin_actor_es_login(session_factory, registry, authorizer, builders):
    ctx = _ctx(session_factory, registry, authorizer, actor=None)
    router = Router(ctx, builders)

    resultado = router.resolve(RUTA_LIBRE.route)

    assert resultado.kind == "login"


def test_build_devuelve_el_control_del_builder(session_factory, registry, authorizer, builders):
    ctx = _ctx(session_factory, registry, authorizer, actor=ACTOR)
    router = Router(ctx, builders)

    control = router.build(RUTA_LIBRE.route)

    assert isinstance(control, ft.Text)
    assert control.value == f"pantalla {RUTA_LIBRE.route}"


def test_build_ruta_prohibida_devuelve_placeholder(session_factory, registry, authorizer, builders):
    ctx = _ctx(session_factory, registry, authorizer, actor=ACTOR)
    router = Router(ctx, builders)

    control = router.build(RUTA_DENEGADA.route)

    assert control is not None
