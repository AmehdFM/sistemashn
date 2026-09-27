"""Errores propios del libro de inventario (plan T2.2)."""

from decimal import Decimal

from sistemashn.core.errors import ValidationError


class InsufficientStock(ValidationError):
    """No hay disponible suficiente para cubrir la operación solicitada."""

    def __init__(self, product_id: int, available: Decimal, requested: Decimal) -> None:
        self.product_id = product_id
        self.available = available
        self.requested = requested
        super().__init__(
            f"existencia insuficiente del producto {product_id}: "
            f"disponible {available}, solicitado {requested}"
        )


class InvalidQuantity(ValidationError):
    """La cantidad indicada no es válida (no positiva o fraccionaria en unidad entera)."""
