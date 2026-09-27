"""Pruebas de la pantalla de cotizaciones."""

import flet as ft

from sistemashn.comercial.ui.cotizaciones_view import build_quotes_view


def test_build_quotes_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_quotes_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_quotes_view_con_cotizacion_no_lanza(ctx_factory, admin_actor, producto_id):
    from datetime import date, timedelta

    from sistemashn.comercial.cotizaciones.schemas import QuoteInput, QuoteLineInput
    from sistemashn.comercial.cotizaciones.service import QuoteService

    ctx = ctx_factory(admin_actor)
    quotes: QuoteService = ctx.service("quotes")
    quotes.create(
        admin_actor,
        QuoteInput(
            lines=[QuoteLineInput(product_id=producto_id, qty="1")],
            valid_until=date.today() + timedelta(days=5),
            request_id="req-1",
        ),
    )

    control = build_quotes_view(ctx)

    assert isinstance(control, ft.Control)


def test_build_quotes_view_vendedor_sin_permiso_no_lanza(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_quotes_view(ctx)

    assert isinstance(control, ft.Control)
