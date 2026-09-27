"""Pruebas de la pantalla de stock bajo."""

import flet as ft

from sistemashn.comercial.ui.low_stock_view import build_low_stock_view


def test_build_low_stock_view_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_low_stock_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_low_stock_view_con_producto(ctx_factory, admin_actor, producto_id):
    ctx = ctx_factory(admin_actor)

    control = build_low_stock_view(ctx)

    assert isinstance(control, ft.Control)
