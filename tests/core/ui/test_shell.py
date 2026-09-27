"""Pruebas de build_shell: construcción sin lanzar y presencia del nombre del negocio."""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.modules.contracts import ScreenDef
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.router import Router
from sistemashn.core.ui.shell import build_shell

RUTA = ScreenDef(
    route="/inicio", label="Inicio", icon="HOME", permission=None, group="General", order=1
)


@dataclass
class FakeRegistry:
    def screens(self) -> list[ScreenDef]:
        return [RUTA]


class FakeAuthorizer:
    def can(self, session, actor, code: str) -> bool:
        return True


def _contiene_texto(control: ft.Control, texto: str) -> bool:
    if isinstance(control, ft.Text) and control.value == texto:
        return True
    for atributo in ("controls", "content", "actions"):
        valor = getattr(control, atributo, None)
        if valor is None:
            continue
        hijos = valor if isinstance(valor, list) else [valor]
        for hijo in hijos:
            if isinstance(hijo, ft.Control) and _contiene_texto(hijo, texto):
                return True
    return False


def test_build_shell_construye_sin_lanzar_y_muestra_el_negocio(session_factory):
    ctx = AppContext(
        session_factory=session_factory,
        registry=FakeRegistry(),
        authorizer=FakeAuthorizer(),
        actor=Actor(user_id=1, username="ana", is_admin=False, session_id="s1"),
        business_name="Repuestos ACME",
    )
    router = Router(ctx, {RUTA.route: lambda c: ft.Text("contenido")})

    control = build_shell(
        ctx, router, RUTA.route, on_navigate=lambda r: None, on_logout=lambda: None
    )

    assert control is not None
    assert _contiene_texto(control, "Repuestos ACME")
