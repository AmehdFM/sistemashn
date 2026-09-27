"""Pruebas de la pantalla de inventario."""

import flet as ft

from sistemashn.comercial.ui.inventory_view import build_inventory_view


def test_build_inventory_view_sin_busqueda_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_inventory_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_inventory_view_vendedor_no_lanza(ctx_factory, vendedor_actor, producto_id):
    ctx = ctx_factory(vendedor_actor)

    control = build_inventory_view(ctx)

    assert isinstance(control, ft.Control)
