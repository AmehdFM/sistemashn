"""Pruebas de la pantalla de punto de venta (POS)."""

import flet as ft

from sistemashn.comercial.ui.pos_view import build_pos_view


def test_build_pos_view_admin_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_pos_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_pos_view_con_producto_no_lanza(ctx_factory, admin_actor, producto_id):
    ctx = ctx_factory(admin_actor)

    control = build_pos_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_pos_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_pos_view(ctx)

    assert isinstance(control, ft.Control)
