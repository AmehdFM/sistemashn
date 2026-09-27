"""Pruebas de restauración consistente de respaldos SQLite hacia base de prueba (T0.3)."""

import sqlite3
from pathlib import Path

import pytest

from sistemashn.core.operations.backup import create_backup, verify_backup
from sistemashn.core.operations.contracts import CorruptBackupError, DestinationExistsError
from sistemashn.core.operations.restore import restore_to_trial


def _make_source_db(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT)")
        connection.execute("INSERT INTO productos (nombre) VALUES ('confirmado-1')")
        connection.commit()
    finally:
        connection.close()


def _make_backup(tmp_path: Path, name: str = "respaldo.db") -> Path:
    source = tmp_path / "origen.db"
    _make_source_db(source)
    destination = tmp_path / name
    create_backup(source, destination)
    return destination


def test_restore_to_trial_copia_datos(tmp_path: Path) -> None:
    backup = _make_backup(tmp_path)
    trial_db = tmp_path / "Mis Respaldos ñ" / "prueba.db"

    result = restore_to_trial(backup, trial_db)

    assert result.verification.ok is True
    assert trial_db.exists()

    check = sqlite3.connect(str(trial_db))
    try:
        names = {row[0] for row in check.execute("SELECT nombre FROM productos")}
    finally:
        check.close()
    assert names == {"confirmado-1"}
    assert not trial_db.with_name(trial_db.name + ".partial").exists()


def test_restore_to_trial_respaldo_corrupto_no_crea_nada(tmp_path: Path) -> None:
    backup = tmp_path / "corrupto.db"
    backup.write_bytes(b"esto no es sqlite" * 10)
    trial_db = tmp_path / "prueba.db"

    with pytest.raises(CorruptBackupError):
        restore_to_trial(backup, trial_db)

    assert not trial_db.exists()
    assert not trial_db.with_name(trial_db.name + ".partial").exists()


def test_restore_to_trial_respaldo_truncado_no_crea_nada(tmp_path: Path) -> None:
    source = tmp_path / "origen.db"
    _make_source_db(source)
    data = source.read_bytes()
    backup = tmp_path / "truncado.db"
    backup.write_bytes(data[: len(data) // 2])
    trial_db = tmp_path / "prueba.db"

    with pytest.raises(CorruptBackupError):
        restore_to_trial(backup, trial_db)

    assert not trial_db.exists()


def test_restore_to_trial_destino_existente_sin_overwrite_falla(tmp_path: Path) -> None:
    backup = _make_backup(tmp_path)
    trial_db = tmp_path / "prueba.db"
    trial_db.write_bytes(b"contenido previo intacto")
    original_bytes = trial_db.read_bytes()

    with pytest.raises(DestinationExistsError):
        restore_to_trial(backup, trial_db)

    assert trial_db.read_bytes() == original_bytes
    assert not trial_db.with_name(trial_db.name + ".partial").exists()


def test_restore_to_trial_destino_existente_con_overwrite(tmp_path: Path) -> None:
    backup = _make_backup(tmp_path)
    trial_db = tmp_path / "prueba.db"
    trial_db.write_bytes(b"contenido previo a reemplazar")

    result = restore_to_trial(backup, trial_db, overwrite=True)

    assert result.verification.ok is True
    verification = verify_backup(trial_db)
    assert verification.ok is True
    assert not trial_db.with_name(trial_db.name + ".partial").exists()
