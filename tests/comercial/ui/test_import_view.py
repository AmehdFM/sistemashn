"""Pruebas de la pantalla de importación/exportación de catálogo."""

import flet as ft

from sistemashn.comercial.ui.import_view import build_import_view


def test_build_import_view_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_import_view(ctx)

    assert isinstance(control, ft.Control)
