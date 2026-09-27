"""Prueba del placeholder de Respaldos."""

import flet as ft
from tests.core.ui.views.conftest import contiene_texto

from sistemashn.core.ui.views.backups_placeholder import build_backups_placeholder


def test_build_backups_placeholder_muestra_mensaje(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_backups_placeholder(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "Disponible en una próxima versión.")
