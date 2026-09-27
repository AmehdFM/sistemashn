"""Errores propios de ventas (plan T4.2)."""

from dataclasses import dataclass
from decimal import Decimal

from sistemashn.core.errors import ValidationError


class InvalidSaleLine(ValidationError):
    """Una línea de la venta no cumple las reglas de negocio (producto inactivo/no existe)."""


class PaymentsMismatch(ValidationError):
    """Los pagos capturados no son válidos para el total de la venta."""


@dataclass(frozen=True)
class PriceOrStockDifference:
    """Una diferencia detectada al convertir una cotización a venta."""

    product_id: int
    field: str  # "unit_price" o "qty_disponible"
    expected: Decimal
    actual: Decimal


class QuoteConversionMismatch(ValidationError):
    """La conversión de la cotización a venta se detuvo por diferencias de precio o stock."""

    def __init__(self, differences: list[PriceOrStockDifference]) -> None:
        self.differences = differences
        detalle = ", ".join(
            f"producto {d.product_id} ({d.field}): esperado {d.expected}, actual {d.actual}"
            for d in differences
        )
        super().__init__(f"la cotización cambió desde que se creó: {detalle}")
