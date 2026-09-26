"""Restauración exclusivamente a una base de prueba nueva."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

from .backup import _integrity, _snapshot, verify_backup
from .contracts import RestoreError, RestoreResult


def restore_to_trial(backup: Path, trial_db: Path) -> RestoreResult:
    result = verify_backup(backup)
    if not result.valid:
        raise RestoreError(result.reason or "La copia no supera verificación")
    if trial_db.exists():
        raise RestoreError("La base de ensayo ya existe")
    trial_db.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=".restore-", dir=trial_db.parent) as directory:
            staged = Path(directory) / trial_db.name
            _snapshot(backup, staged)
            if not _integrity(staged):
                raise RestoreError("La restauración no supera integrity_check")
            if trial_db.exists():
                raise RestoreError("La base de ensayo ya existe")
            os.replace(staged, trial_db)
    except (OSError, sqlite3.Error) as exc:
        raise RestoreError(str(exc)) from exc
    return RestoreResult(backup, trial_db, result)
