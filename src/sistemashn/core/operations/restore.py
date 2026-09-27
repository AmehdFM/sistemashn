"""Restauración de respaldos SQLite hacia una base de prueba (solo librería estándar)."""

import os
import sqlite3
from pathlib import Path

from sistemashn.core.operations.backup import verify_backup
from sistemashn.core.operations.contracts import (
    CorruptBackupError,
    DestinationExistsError,
    RestoreResult,
    VerificationResult,
)


def restore_to_trial(backup: Path, trial_db: Path, *, overwrite: bool = False) -> RestoreResult:
    """Restaura `backup` hacia `trial_db`, verificando integridad antes y después.

    Nunca deja un archivo a medias en `trial_db`: si algo falla, no se toca el destino.
    """
    verification = verify_backup(backup)
    if not verification.ok:
        raise CorruptBackupError(
            f"El respaldo {backup} no pasó la verificación: {verification.integrity}"
        )

    if trial_db.exists() and not overwrite:
        raise DestinationExistsError(f"El destino ya existe: {trial_db}")

    trial_db.parent.mkdir(parents=True, exist_ok=True)
    partial = trial_db.with_name(trial_db.name + ".partial")
    if partial.exists():
        partial.unlink()

    backup_connection: sqlite3.Connection | None = None
    partial_connection: sqlite3.Connection | None = None
    try:
        backup_connection = sqlite3.connect(f"{backup.as_uri()}?mode=ro", uri=True)
        partial_connection = sqlite3.connect(str(partial))
        backup_connection.backup(partial_connection)
        partial_connection.commit()
    except sqlite3.Error:
        if partial_connection is not None:
            partial_connection.close()
            partial_connection = None
        partial.unlink(missing_ok=True)
        raise
    finally:
        if partial_connection is not None:
            partial_connection.close()
        if backup_connection is not None:
            backup_connection.close()

    final_verification = verify_backup(partial)
    if not final_verification.ok:
        partial.unlink(missing_ok=True)
        raise CorruptBackupError(
            f"La copia restaurada de {backup} no pasó la verificación: "
            f"{final_verification.integrity}"
        )

    os.replace(partial, trial_db)
    final_verification = VerificationResult(
        path=trial_db,
        ok=final_verification.ok,
        integrity=final_verification.integrity,
        sha256=final_verification.sha256,
        schema_revision=final_verification.schema_revision,
        size_bytes=final_verification.size_bytes,
    )
    return RestoreResult(
        backup=backup,
        target=trial_db,
        verification=final_verification,
    )
