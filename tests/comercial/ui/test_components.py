"""Pruebas de los helpers puros compartidos de la UI de Comercial."""

from decimal import Decimal

import flet as ft
import pytest

from sistemashn.comercial.ui.components import (
    adjust_button,
    parse_decimal,
    parse_optional_decimal,
    stock_and_movements_section,
    validate_reason,
)


def test_parse_decimal_valido():
    assert parse_decimal("10.5", "cantidad") == Decimal("10.5")


def test_parse_decimal_vacio_lanza():
    with pytest.raises(ValueError):
        parse_decimal("", "cantidad")


def test_parse_decimal_invalido_lanza():
    with pytest.raises(ValueError):
        parse_decimal("xyz", "cantidad")


def test_parse_optional_decimal_vacio_es_none():
    assert parse_optional_decimal("") is None


def test_parse_optional_decimal_valido():
    assert parse_optional_decimal("5") == Decimal("5")


def test_validate_reason_corto_lanza():
    with pytest.raises(ValueError):
        validate_reason("abc")


def test_validate_reason_valido_recorta():
    assert validate_reason("  motivo largo  ") == "motivo largo"


def test_stock_and_movements_section_no_lanza(ctx_factory, admin_actor, producto_id):
    ctx = ctx_factory(admin_actor)

    control = stock_and_movements_section(ctx, producto_id, 1, lambda _p: None)

    assert isinstance(control, ft.Control)


def test_adjust_button_none_sin_permiso(ctx_factory, vendedor_actor, producto_id):
    ctx = ctx_factory(vendedor_actor)

    assert adjust_button(ctx, producto_id, lambda: None) is None


def test_adjust_button_presente_con_permiso(ctx_factory, admin_actor, producto_id):
    ctx = ctx_factory(admin_actor)

    assert adjust_button(ctx, producto_id, lambda: None) is not None
