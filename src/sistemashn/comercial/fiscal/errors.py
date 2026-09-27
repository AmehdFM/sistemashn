"""Errores propios de facturación fiscal (plan T4.5)."""

from sistemashn.core.errors import ValidationError


class FiscalDisabled(ValidationError):
    """El negocio no tiene habilitada la emisión de factura fiscal (`fiscal_enabled=False`)."""


class NoActiveAuthorization(ValidationError):
    """No hay ninguna autorización CAI activa para el tipo de documento solicitado."""


class AuthorizationExhausted(ValidationError):
    """La autorización CAI ya consumió todo su rango de correlativos."""


class AuthorizationExpired(ValidationError):
    """La autorización CAI ya pasó su fecha límite de vigencia."""


class AlreadyInvoiced(ValidationError):
    """Ya existe una factura fiscal emitida para esta venta."""
