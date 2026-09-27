"""Contratos de datos y errores para operaciones de respaldo/restauración de SQLite."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class VerificationResult:
    """Resultado de verificar la integridad de un archivo SQLite."""

    path: Path
    ok: bool
    integrity: str
    sha256: str
    schema_revision: str | None
    size_bytes: int


@dataclass(frozen=True)
class BackupReceipt:
    """Comprobante de un respaldo creado exitosamente."""

    source: Path
    destination: Path
    created_at: datetime
    verification: VerificationResult


@dataclass(frozen=True)
class RestoreResult:
    """Resultado de restaurar un respaldo hacia un destino (por ejemplo, base de prueba)."""

    backup: Path
    target: Path
    verification: VerificationResult


class OperationError(Exception):
    """Error base para operaciones de respaldo/restauración."""


class BackupError(OperationError):
    """Error al crear un respaldo."""


class RestoreError(OperationError):
    """Error al restaurar un respaldo."""


class CorruptBackupError(RestoreError):
    """El archivo de respaldo no pasó la verificación de integridad."""


class DestinationExistsError(OperationError):
    """El destino ya existe y no se solicitó sobrescritura."""
