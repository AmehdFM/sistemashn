"""Pruebas de widgets puros: formato de dinero y construcción sin lanzar (T1.6a)."""

from __future__ import annotations

from decimal import Decimal

import flet as ft
import pytest

from sistemashn.core.pagination import Page
from sistemashn.core.ui import widgets


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("1234.5"), "L 1,234.50"),
        (Decimal("0"), "L 0.00"),
        (Decimal("-5"), "-L 5.00"),
        (Decimal("1234567.89"), "L 1,234,567.89"),
    ],
)
def test_format_lempiras(valor, esperado):
    assert widgets.format_lempiras(valor) == esperado


def test_money_text_usa_el_mismo_formato():
    control = widgets.money_text(Decimal("10.5"))
    assert isinstance(control, ft.Text)
    assert control.value == "L 10.50"


def test_empty_state_construye_sin_lanzar():
    assert widgets.empty_state("Sin datos") is not None


def test_error_banner_construye_sin_lanzar():
    assert widgets.error_banner("Algo falló") is not None


def test_loading_construye_sin_lanzar():
    assert widgets.loading() is not None


def test_forbidden_view_construye_sin_lanzar():
    assert widgets.forbidden_view() is not None


def test_not_found_view_construye_sin_lanzar():
    assert widgets.not_found_view() is not None


def test_form_field_construye_sin_lanzar():
    campo = widgets.form_field("Usuario", value="ana", autofocus=True)
    assert isinstance(campo, ft.TextField)
    assert campo.value == "ana"


def test_primary_y_secondary_button_construyen_sin_lanzar():
    assert widgets.primary_button("Guardar", lambda e: None) is not None
    assert widgets.secondary_button("Cancelar", lambda e: None) is not None


def test_confirm_dialog_construye_sin_lanzar():
    dialog = widgets.confirm_dialog("Confirmar", "¿Seguro?", lambda: None)
    assert isinstance(dialog, ft.AlertDialog)
    assert len(dialog.actions) == 2


def test_paginated_table_construye_sin_lanzar():
    page = Page(items=[1, 2], total=25, page=2, page_size=10)
    tabla = widgets.paginated_table(
        columns=["Nombre", "Rol"],
        rows=[[ft.Text("Ana"), ft.Text("Admin")], [ft.Text("Beto"), ft.Text("Vendedor")]],
        page=page,
        on_page_change=lambda p: None,
    )
    assert tabla is not None
