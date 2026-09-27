"""Respaldo y verificación de bases de datos SQLite (solo librería estándar)."""

import hashlib
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sistemashn.core.operations.contracts import (
    BackupError,
    BackupReceipt,
    DestinationExistsError,
    VerificationResult,
)

_HASH_CHUNK_SIZE = 1024 * 1024


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_only_uri(path: Path) -> str:
    # Path.as_uri() codifica espacios y acentos correctamente para Windows.
    return f"{path.as_uri()}?mode=ro"


def verify_backup(path: Path) -> VerificationResult:
    """Verifica que `path` sea un archivo SQLite íntegro, sin modificarlo."""
    size_bytes = path.stat().st_size if path.exists() else 0

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(_read_only_uri(path), uri=True)
        cursor = connection.execute("PRAGMA integrity_check")
        rows = [str(row[0]) for row in cursor.fetchall()]
        integrity = "; ".join(rows) if rows else "sin resultado"
        ok = rows == ["ok"]

        schema_revision: str | None = None
        if ok:
            table_check = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            if table_check is not None:
                revision_row = connection.execute(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                ).fetchone()
                if revision_row is not None:
                    schema_revision = str(revision_row[0])
    except sqlite3.Error as exc:
        ok = False
        integrity = f"error al abrir/leer la base: {exc}"
        schema_revision = None
    finally:
        if connection is not None:
            connection.close()

    sha256 = _sha256_of(path) if path.exists() else ""
    return VerificationResult(
        path=path,
        ok=ok,
        integrity=integrity,
        sha256=sha256,
        schema_revision=schema_revision,
        size_bytes=size_bytes,
    )


def default_backup_name(now: datetime) -> str:
    """Genera un nombre de archivo de respaldo a partir de una fecha/hora."""
    return f"sistemashn-{now.strftime('%Y%m%d-%H%M%S')}.db"


def create_backup(source: Path, destination: Path) -> BackupReceipt:
    """Crea un respaldo consistente de `source` en `destination`.

    Usa la API de respaldo online de SQLite (`Connection.backup`), que solo copia
    datos confirmados incluso si hay otra conexión con una transacción abierta.
    """
    if destination.exists():
        raise DestinationExistsError(f"El destino ya existe: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        partial.unlink()

    source_connection: sqlite3.Connection | None = None
    partial_connection: sqlite3.Connection | None = None
    try:
        source_connection = sqlite3.connect(_read_only_uri(source), uri=True)
        partial_connection = sqlite3.connect(str(partial))
        source_connection.backup(partial_connection)
        # Un solo archivo portable, sin -wal/-shm asociados.
        partial_connection.execute("PRAGMA journal_mode=DELETE")
        partial_connection.commit()
    except sqlite3.Error as exc:
        if partial_connection is not None:
            partial_connection.close()
        if source_connection is not None:
            source_connection.close()
        if partial.exists():
            partial.unlink()
        raise BackupError(f"No se pudo crear el respaldo de {source}: {exc}") from exc
    finally:
        if partial_connection is not None:
            partial_connection.close()
        if source_connection is not None:
            source_connection.close()

    verification = verify_backup(partial)
    if not verification.ok:
        partial.unlink(missing_ok=True)
        raise BackupError(
            f"El respaldo de {source} no pasó la verificación: {verification.integrity}"
        )

    os.replace(partial, destination)
    verification = VerificationResult(
        path=destination,
        ok=verification.ok,
        integrity=verification.integrity,
        sha256=verification.sha256,
        schema_revision=verification.schema_revision,
        size_bytes=verification.size_bytes,
    )
    return BackupReceipt(
        source=source,
        destination=destination,
        created_at=datetime.now(UTC),
        verification=verification,
    )
