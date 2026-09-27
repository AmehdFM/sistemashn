"""Errores propios de devoluciones (plan T5.2/T5.3)."""

from sistemashn.core.errors import ValidationError


class ReturnExceedsOriginal(ValidationError):
    """La cantidad devuelta (sumada a devoluciones previas) supera lo vendido o comprado."""


class InvalidReturnResolution(ValidationError):
    """La resolución elegida no aplica a los datos de la devolución (p. ej. falta el pago)."""
