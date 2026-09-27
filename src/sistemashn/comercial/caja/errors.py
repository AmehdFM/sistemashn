"""Errores propios de caja (plan T4.3)."""

from sistemashn.core.errors import ValidationError


class CashSessionAlreadyOpen(ValidationError):
    """Ya hay una sesión de caja abierta: debe cerrarse antes de abrir otra."""


class NoCashSessionOpen(ValidationError):
    """La operación requiere una sesión de caja abierta y no hay ninguna."""
