"""Pruebas de los diálogos de unidades y categorías (embebidos en /catalogo)."""

import flet as ft

from sistemashn.comercial.ui.units_categories_view import (
    open_categories_dialog,
    open_units_dialog,
)


class _FakeControl(ft.Text):
    """Control mínimo con `page=None`, para probar que abrir el diálogo no lanza."""


def test_open_units_dialog_sin_page_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)
    control = _FakeControl("x")

    open_units_dialog(ctx, control, lambda: None)


def test_open_categories_dialog_sin_page_no_lanza(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)
    control = _FakeControl("x")

    open_categories_dialog(ctx, control, lambda: None)
