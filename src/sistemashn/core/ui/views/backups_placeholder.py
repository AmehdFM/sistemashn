"""Placeholder de Respaldos: la funcionalidad llega en la Fase 6 (T1.6b-2)."""

from __future__ import annotations

import flet as ft

from sistemashn.core.ui import theme, widgets
from sistemashn.core.ui.app_context import AppContext


def build_backups_placeholder(ctx: AppContext) -> ft.Control:
    return ft.Column(
        controls=[
            widgets.page_header("Respaldos"),
            widgets.empty_state("Disponible en una próxima versión.", icon=ft.Icons.BACKUP),
        ],
        spacing=theme.SPACING["md"],
        expand=True,
    )
