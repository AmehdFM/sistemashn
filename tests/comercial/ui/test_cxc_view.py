"""Pruebas de la pantalla de cuentas por cobrar (CxC)."""

import flet as ft

from sistemashn.comercial.ui.cxc_view import build_receivables_view


def test_build_cxc_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_receivables_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_cxc_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_receivables_view(ctx)

    assert isinstance(control, ft.Control)
