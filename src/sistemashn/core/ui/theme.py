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
TEXT_MUTED = "#52525B"
TABLE_HEADER_BG = "#F4F4F5"

# Estados (contraste AA sobre fondo claro)
SUCCESS = "#15803D"
WARNING = "#B45309"
ERROR = "#B91C1C"
INFO = "#1D4ED8"

# Espaciado y radios
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}
RADIUS = 8
FONT_CAPTION = 12
FONT_BODY = 14
FONT_SUBTITLE = 20
FONT_TITLE = 28


def build_theme() -> ft.Theme:
    """Tema Material con la jerarquía tipográfica de escritorio Windows."""
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=PRIMARY,
            on_primary=SURFACE,
            surface=SURFACE,
            on_surface=TEXT,
            on_surface_variant=TEXT_MUTED,
            outline=BORDER,
        ),
        font_family="Segoe UI",
        text_theme=ft.TextTheme(
            body_small=ft.TextStyle(size=FONT_CAPTION, height=16 / FONT_CAPTION, color=TEXT),
            body_medium=ft.TextStyle(size=FONT_BODY, height=20 / FONT_BODY, color=TEXT),
            body_large=ft.TextStyle(size=18, height=24 / 18, color=TEXT),
            label_medium=ft.TextStyle(size=FONT_CAPTION, height=16 / FONT_CAPTION, color=TEXT),
            label_large=ft.TextStyle(size=FONT_BODY, height=20 / FONT_BODY, color=TEXT),
            title_medium=ft.TextStyle(
                size=FONT_SUBTITLE,
                height=28 / FONT_SUBTITLE,
                weight=ft.FontWeight.W_600,
                color=TEXT,
            ),
            title_large=ft.TextStyle(
                size=FONT_TITLE, height=36 / FONT_TITLE, weight=ft.FontWeight.W_600, color=TEXT
            ),
        ),
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
        window.min_height = 700
