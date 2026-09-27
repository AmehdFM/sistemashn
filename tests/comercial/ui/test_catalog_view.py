"""Pruebas de la pantalla de catálogo: construcción, permisos y helpers puros."""

from decimal import Decimal

import flet as ft
import pytest
from tests.comercial.ui.conftest import contiene_texto

from sistemashn.comercial.ui.catalog_view import build_catalog_view, parse_price, parse_quantity


def test_build_catalog_view_admin_sin_datos_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_catalog_view(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "Nuevo producto")


def test_build_catalog_view_con_producto(ctx_factory, admin_actor, producto_id):
    ctx = ctx_factory(admin_actor)

    control = build_catalog_view(ctx)

    assert isinstance(control, ft.Control)
    assert contiene_texto(control, "ABC-123")


def test_vendedor_no_ve_boton_nuevo_producto(ctx_factory, vendedor_actor):
    ctx = ctx_factory(vendedor_actor)

    control = build_catalog_view(ctx)

    assert isinstance(control, ft.Control)
    assert not contiene_texto(control, "Nuevo producto")


def test_parse_price_valido():
    assert parse_price("150.50") == Decimal("150.50")


def test_parse_price_con_comas():
    assert parse_price("1,250.00") == Decimal("1250.00")


def test_parse_price_vacio_lanza():
    with pytest.raises(ValueError):
        parse_price("")


def test_parse_price_invalido_lanza():
    with pytest.raises(ValueError):
        parse_price("abc")


def test_parse_quantity_valido():
    assert parse_quantity("3") == Decimal("3")
