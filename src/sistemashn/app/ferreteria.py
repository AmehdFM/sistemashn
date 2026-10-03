"""Composición y arranque de SistemasHN Ferretería."""

from __future__ import annotations

import flet as ft

from sistemashn.app.bootstrap import build_context
from sistemashn.comercial.ui.screens import COMERCIAL_SCREEN_BUILDERS
from sistemashn.core.ui.app_shell import DesktopApp
from sistemashn.core.ui.router import ScreenBuilder
from sistemashn.core.ui.screens import CORE_SCREEN_BUILDERS
from sistemashn.ferreteria.ui.screens import FERRETERIA_SCREEN_BUILDERS

_SCREEN_BUILDERS: dict[str, ScreenBuilder] = {
    **CORE_SCREEN_BUILDERS,
    **COMERCIAL_SCREEN_BUILDERS,
    **FERRETERIA_SCREEN_BUILDERS,
}


def main(page: ft.Page) -> None:
    ctx = build_context(vertical="ferreteria")
    DesktopApp(ctx, builders=_SCREEN_BUILDERS).mount(page)
