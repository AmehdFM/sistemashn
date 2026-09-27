"""Composición de la aplicación de escritorio: decide la vista y gestiona la navegación."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal

import flet as ft

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.errors import PermissionDenied, SistemasHNError
from sistemashn.core.setup.service import SetupStep
from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext
from sistemashn.core.ui.login_view import build_login_view
from sistemashn.core.ui.router import Router, ScreenBuilder
from sistemashn.core.ui.setup_view import build_setup_view
from sistemashn.core.ui.shell import build_shell

ViewKind = Literal["setup", "login", "shell"]

_logger = logging.getLogger("sistemashn")
_MENSAJE_SIN_PERMISO = "No tiene permiso para realizar esta acción."
_MENSAJE_INESPERADO = "Ocurrió un error inesperado. Consulte el registro de la aplicación."


def _configure_logging(data_dir: Path) -> None:
    """Envía el registro de la aplicación a `data_dir/logs/app.log` (rotación 1 MB x 5)."""
    if _logger.handlers:
        return
    carpeta = data_dir / "logs"
    carpeta.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        carpeta / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


def initial_view_kind(ctx: AppContext) -> ViewKind:
    """Decide qué vista mostrar según el estado del primer arranque y la sesión actual."""
    setup_service = ctx.service("setup")
    state = setup_service.state()
    if state.step != SetupStep.DONE:
        return "setup"
    if ctx.actor is None:
        return "login"
    return "shell"


class DesktopApp:
    """Compone la vista adecuada (asistente, login o cascarón) y gestiona la navegación."""

    def __init__(self, ctx: AppContext, builders: dict[str, ScreenBuilder]) -> None:
        self.ctx = ctx
        self.builders = builders
        self.router = Router(ctx, builders)
        self.current_route = "/"
        self.pending_error: str | None = None
        self.page: ft.Page | None = None
        if ctx.data_dir is not None:
            _configure_logging(ctx.data_dir)

    def mount(self, page: ft.Page) -> None:
        """Aplica el tema y renderiza la vista inicial en `page`."""
        self.page = page
        page.title = f"SistemasHN {self.ctx.business_name}"
        # Tamaño mínimo para que la barra lateral y los formularios quepan sin recortarse.
        page.window.min_width = 1024
        page.window.min_height = 700
        theme.apply_page_theme(page)
        self._render()

    def _guard(self, accion) -> None:
        """Ejecuta `accion` capturando errores de servicio antes de volver a renderizar."""
        try:
            accion()
            self.pending_error = None
        except PermissionDenied:
            self.pending_error = _MENSAJE_SIN_PERMISO
        except SistemasHNError as exc:
            self.pending_error = str(exc)
        except Exception:
            _logger.exception("error inesperado en la interfaz")
            self.pending_error = _MENSAJE_INESPERADO
        self._render()

    def _render(self) -> None:
        assert self.page is not None
        kind = initial_view_kind(self.ctx)
        if kind == "setup":
            content = build_setup_view(self.ctx, on_done=self._on_setup_done)
        elif kind == "login":
            content = build_login_view(self.ctx, on_login=self._on_login)
        else:
            content = self._build_shell_content()

        self.page.controls = [content]
        self.page.update()

    def _build_shell_content(self) -> ft.Control:
        visibles = self.router.visible_screens()
        if not visibles:
            contenido: ft.Control = widgets.empty_state(
                f"Bienvenido a {self.ctx.business_name}. Aún no tiene pantallas asignadas.",
                icon=ft.Icons.HOME,
            )
        else:
            if not any(s.route == self.current_route for s in visibles):
                self.current_route = visibles[0].route
            contenido = build_shell(
                self.ctx, self.router, self.current_route, self._on_navigate, self._on_logout
            )

        if self.pending_error:
            return ft.Column(
                controls=[widgets.error_banner(self.pending_error), contenido],
                spacing=theme.SPACING["sm"],
                expand=True,
            )
        return contenido

    def _on_setup_done(self) -> None:
        self._render()

    def _on_login(self, actor: Actor) -> None:
        self.ctx.actor = actor
        business = self.ctx.service("settings").get_business()
        if business is not None:
            self.ctx.business_name = business.name
            self.ctx.show_logo_in_app = business.show_logo_in_app
        perfil = (
            self.ctx.registry.profiles().get(actor.profile_code) if actor.profile_code else None
        )
        if perfil is not None and perfil.home_route is not None:
            self.current_route = perfil.home_route
        self._render()

    def _on_logout(self) -> None:
        def _accion() -> None:
            self.ctx.service("identity").logout(self.ctx.actor)
            self.ctx.actor = None
            self.current_route = "/"

        self._guard(_accion)

    def _on_navigate(self, route: str) -> None:
        def _accion() -> None:
            self.current_route = route

        self._guard(_accion)
