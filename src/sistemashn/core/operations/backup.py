"""Copia SQLite consistente; manifiesto de integridad junto al archivo."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from .contracts import BackupError, BackupReceipt, VerificationResult


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)


def _revision(path: Path) -> str | None:
    with _connect_readonly(path) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='alembic_version'").fetchone():
            return None
        row = db.execute("SELECT version_num FROM alembic_version").fetchone()
        return None if row is None else row[0]


def _integrity(path: Path) -> bool:
    with _connect_readonly(path) as db:
        return db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def _snapshot(source: Path, destination: Path) -> None:
    with _connect_readonly(source) as input_db:
        with sqlite3.connect(destination) as output_db:
            input_db.backup(output_db)


def _manifest(path: Path) -> Path:
    return path.with_name(path.name + ".manifest.json")


def verify_backup(path: Path) -> VerificationResult:
    try:
        metadata = json.loads(_manifest(path).read_text(encoding="utf-8"))
        if metadata.get("format") != 1:
            raise ValueError("Formato de manifiesto desconocido")
        integrity = _integrity(path)
        hash_ok = _sha256(path) == metadata["sha256"]
        revision = _revision(path)
        revision_ok = revision == metadata["revision"]
        return VerificationResult(path, integrity and hash_ok and revision_ok, integrity, hash_ok, revision_ok, revision)
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        return VerificationResult(path, False, False, False, False, reason=str(exc))


def create_backup(source: Path, destination: Path) -> BackupReceipt:
    if not source.is_file() or destination.exists() or _manifest(destination).exists():
        raise BackupError("Origen inexistente o destino ocupado")
    destination.parent.mkdir(parents=True, exist_ok=True)
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix=".backup-", dir=destination.parent) as directory:
            staged = Path(directory) / "snapshot.sqlite3"
            _snapshot(source, staged)
            if not _integrity(staged):
                raise BackupError("La copia SQLite no supera integrity_check")
            revision = _revision(staged)
            sha256 = _sha256(staged)
            staged_manifest = Path(directory) / "manifest.json"
            staged_manifest.write_text(json.dumps({"format": 1, "sha256": sha256, "revision": revision}), encoding="utf-8")
            os.replace(staged, destination)
            published = True
            os.replace(staged_manifest, _manifest(destination))
        if not verify_backup(destination).valid:
            raise BackupError("La copia publicada no supera verificación")
        return BackupReceipt(destination, _manifest(destination), sha256, revision)
    except (OSError, sqlite3.Error) as exc:
        raise BackupError(str(exc)) from exc
    finally:
        if published and not _manifest(destination).exists():
            destination.unlink(missing_ok=True)
