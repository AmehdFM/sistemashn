"""Puntos de extensión de la UI comercial que las verticales implementan."""

from typing import Protocol

import flet as ft

from sistemashn.core.ui.app_context import AppContext


class ProductFormExtension(Protocol):
    """Sección adicional del detalle de producto (p. ej. datos de parte en Repuestos).

    `build` devuelve una sección autocontenida: carga sus datos con sus propios servicios y
    guarda con sus propios botones. Se muestra solo para productos ya creados.
    """

    title: str

    def is_visible(self, ctx: AppContext) -> bool: ...

    def build(self, ctx: AppContext, product_id: int) -> ft.Control: ...


PRODUCT_FORM_EXTENSIONS_KEY = "comercial.product_form_extensions"
"""Clave en `ctx.services` con `list[ProductFormExtension]` registrada por la aplicación."""
