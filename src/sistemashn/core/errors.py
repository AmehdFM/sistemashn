"""Jerarquía de errores de dominio de SistemasHN."""


class SistemasHNError(Exception):
    """Base de todos los errores de dominio."""


class PermissionDenied(SistemasHNError):
    """El actor no tiene permiso para realizar la operación."""


class ValidationError(SistemasHNError):
    """Los datos de entrada no cumplen las reglas de negocio."""


class NotFound(SistemasHNError):
    """El recurso solicitado no existe."""


class DatabaseBusyError(SistemasHNError):
    """La base de datos permaneció bloqueada tras agotar los reintentos."""


class AuthenticationError(SistemasHNError):
    """Fallo de autenticación (login o recuperación): mensaje genérico para el usuario."""
