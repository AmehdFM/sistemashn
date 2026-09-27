"""Errores propios de compras (plan T3.2)."""

from sistemashn.core.errors import ValidationError


class PaymentsExceedTotal(ValidationError):
    """La suma de los pagos capturados excede el total de la compra."""


class InvalidPurchaseLine(ValidationError):
    """Una línea de la compra no cumple las reglas de negocio (producto inactivo o kit)."""
