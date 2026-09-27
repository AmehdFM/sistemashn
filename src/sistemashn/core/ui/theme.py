"""Tokens visuales de la aplicación (spec §6: paleta Grafito y Vino) y tema de Flet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from flet import Page

# Paleta principal
PRIMARY = "#8B2635"
PRIMARY_DARK = "#6E1E2A"

# Barra lateral (Grafito)
SIDEBAR = "#27272A"
SIDEBAR_TEXT = "#FAFAF9"
SIDEBAR_MUTED = "#A1A1AA"

# Área de contenido
CONTENT_BG = "#FAFAF9"
SURFACE = "#FFFFFF"
BORDER = "#E4E4E7"
TEXT = "#18181B"
TEXT_MUTED = "#71717A"

# Estados (contraste AA sobre fondo claro)
SUCCESS = "#15803D"
WARNING = "#B45309"
ERROR = "#B91C1C"
INFO = "#1D4ED8"

# Espaciado y radios
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
RADIUS = 8


def build_theme() -> ft.Theme:
    """Tema Material construido a partir del color primario de marca."""
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        color_scheme=ft.ColorScheme(primary=PRIMARY),
        use_material3=True,
    )


def apply_page_theme(page: Page) -> None:
    """Aplica tema claro, fondo y tamaño mínimo de ventana a la página."""
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = build_theme()
    page.bgcolor = CONTENT_BG
    page.padding = 0

    window = getattr(page, "window", None)
    if window is not None:
        window.min_width = 1024
        window.min_height = 640
