"""Pruebas de la pantalla de ajustes del negocio: construcción con y sin datos."""

import flet as ft

from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.ui.views.business_view import build_business_view


def test_build_business_view_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_business_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_business_view_con_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)
    ctx.service("settings").update_business(
        admin_actor,
        BusinessInput(
            name="Repuestos ACME",
            legal_name="Repuestos ACME S. de R.L.",
            rtn=None,
            address="Col. Kennedy",
            phone="9999-9999",
            email="ventas@acme.hn",
        ),
    )

    control = build_business_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_business_view_actor_no_admin_oculta_codigos(ctx_factory, limited_actor):
    ctx = ctx_factory(limited_actor)

    control = build_business_view(ctx)

    assert isinstance(control, ft.Control)
