"""Enrutador de la UI: pantallas visibles según permisos y resolución de rutas."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import flet as ft

from sistemashn.core.db.session import session_scope
from sistemashn.core.modules.contracts import ScreenDef
from sistemashn.core.ui import widgets
from sistemashn.core.ui.app_context import AppContext

ScreenBuilder = Callable[[AppContext], ft.Control]

RouteKind = Literal["login", "forbidden", "not_found", "ok"]


@dataclass(frozen=True)
class RouteResult:
    kind: RouteKind
    screen: ScreenDef | None


class Router:
    """Calcula el menú visible y resuelve/renderiza rutas verificando permisos siempre."""

    def __init__(self, ctx: AppContext, builders: dict[str, ScreenBuilder]) -> None:
        self.ctx = ctx
        self.builders = builders

    def _puede_ver(self, screen: ScreenDef) -> bool:
        if screen.permission is None:
            return True
        if self.ctx.actor is None:
            return False
        with session_scope(self.ctx.session_factory, readonly=True) as session:
            return self.ctx.authorizer.can(session, self.ctx.actor, screen.permission)

    def visible_screens(self) -> list[ScreenDef]:
        """Pantallas que el actor actual puede ver, con builder registrado, ordenadas."""
        if self.ctx.actor is None:
            return []

        pantallas = [
            screen
            for screen in self.ctx.registry.screens()
            if screen.route in self.builders and self._puede_ver(screen)
        ]
        return sorted(pantallas, key=lambda s: (s.group, s.order))

    def resolve(self, route: str) -> RouteResult:
        """Resuelve una ruta verificando el permiso de nuevo (no confía en el menú)."""
        if self.ctx.actor is None:
            return RouteResult(kind="login", screen=None)

        screen = next(
            (s for s in self.ctx.registry.screens() if s.route == route),
            None,
        )
        if screen is None or route not in self.builders:
            return RouteResult(kind="not_found", screen=None)

        if not self._puede_ver(screen):
            return RouteResult(kind="forbidden", screen=screen)

        return RouteResult(kind="ok", screen=screen)

    def build(self, route: str) -> ft.Control:
        """Construye el control de la ruta o un placeholder (prohibido/no encontrado/login)."""
        resultado = self.resolve(route)
        if resultado.kind == "forbidden":
            return widgets.forbidden_view()
        if resultado.kind == "not_found":
            return widgets.not_found_view()
        if resultado.kind == "login":
            return widgets.empty_state("Inicie sesión para continuar.", icon=ft.Icons.LOCK)

        assert resultado.screen is not None
        return self.builders[resultado.screen.route](self.ctx)
