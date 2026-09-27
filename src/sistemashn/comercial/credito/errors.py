"""Errores propios de cuentas por pagar/cobrar (plan T3.3)."""

from sistemashn.core.errors import ValidationError


class InvalidAccountKind(ValidationError):
    """`kind` debe ser 'payable' (cuenta por pagar) o 'receivable' (cuenta por cobrar)."""


class RequestIdReused(ValidationError):
    """El `request_id` ya se usó para abonar una cuenta distinta."""


class OverpaymentError(ValidationError):
    """El monto del abono excede el saldo pendiente de la cuenta."""
