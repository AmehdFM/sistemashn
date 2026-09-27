"""Pruebas de la pantalla de caja."""

import flet as ft

from sistemashn.comercial.ui.caja_view import build_cash_view


def test_build_cash_view_admin_sin_sesion_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_cash_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_cash_view_con_sesion_abierta_no_lanza(ctx_factory, admin_actor):
    from sistemashn.comercial.caja.service import CashService

    ctx = ctx_factory(admin_actor)
    cash: CashService = ctx.service("cash")
    cash.open(admin_actor, "100.00")

    control = build_cash_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_cash_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_cash_view(ctx)

    assert isinstance(control, ft.Control)
