"""Pruebas de la pantalla de cuentas por pagar (CxP)."""

import flet as ft

from sistemashn.comercial.ui.cxp_view import build_cxp_view


def test_build_cxp_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_cxp_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_cxp_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_cxp_view(ctx)

    assert isinstance(control, ft.Control)
