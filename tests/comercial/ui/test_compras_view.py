"""Pruebas de las pantallas de compras: historial y captura de compra nueva."""

import flet as ft

from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.contrapartes.service import PartyService
from sistemashn.comercial.ui.compras_view import build_new_purchase_view, build_purchases_view


def test_build_purchases_view_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_purchases_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_purchases_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_purchases_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_new_purchase_view_admin_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_new_purchase_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_new_purchase_view_con_proveedor_no_lanza(ctx_factory, admin_actor, producto_id):
    ctx = ctx_factory(admin_actor)
    parties: PartyService = ctx.service("parties")
    parties.create(
        admin_actor, PartyInput(kind=PartyKind.NEGOCIO, name="Proveedor Uno", is_supplier=True)
    )

    control = build_new_purchase_view(ctx)

    assert isinstance(control, ft.Control)
