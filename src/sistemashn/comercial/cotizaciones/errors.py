"""Errores propios de cotizaciones (plan T4.1)."""

from sistemashn.core.errors import ValidationError


class InvalidQuoteLine(ValidationError):
    """Una línea de la cotización no cumple las reglas de negocio (producto inactivo)."""


class InvalidQuoteStatus(ValidationError):
    """La operación no es válida para el estado actual de la cotización."""
