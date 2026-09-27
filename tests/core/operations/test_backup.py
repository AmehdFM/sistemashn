"""Pruebas de respaldo/verificación consistente de SQLite (T0.3)."""

import sqlite3
from datetime import UTC, timedelta
from pathlib import Path

import pytest

from sistemashn.core.operations.backup import create_backup, default_backup_name, verify_backup
from sistemashn.core.operations.contracts import BackupError, DestinationExistsError


def _make_source_db(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT)")
        connection.execute("INSERT INTO productos (nombre) VALUES ('confirmado-1')")
        connection.execute("INSERT INTO productos (nombre) VALUES ('confirmado-2')")
        connection.commit()
    finally:
        connection.close()


def test_verify_backup_de_archivo_valido(tmp_path: Path) -> None:
    source = tmp_path / "origen.db"
    _make_source_db(source)

    result = verify_backup(source)

    assert result.ok is True
    assert result.integrity == "ok"
    assert result.size_bytes > 0
    assert len(result.sha256) == 64


def test_verify_backup_lee_revision_alembic(tmp_path: Path) -> None:
    source = tmp_path / "origen.db"
    _make_source_db(source)
    connection = sqlite3.connect(str(source))
    try:
        connection.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
        connection.execute("INSERT INTO alembic_version VALUES ('0001_inicial')")
        connection.commit()
    finally:
        connection.close()

    result = verify_backup(source)

    assert result.ok is True
    assert result.schema_revision == "0001_inicial"


def test_verify_backup_sin_tabla_alembic_da_none(tmp_path: Path) -> None:
    source = tmp_path / "origen.db"
    _make_source_db(source)

    result = verify_backup(source)

    assert result.schema_revision is None


def test_verify_backup_archivo_no_sqlite(tmp_path: Path) -> None:
    path = tmp_path / "basura.db"
    path.write_bytes(b"esto no es una base de datos sqlite" * 10)

    result = verify_backup(path)

    assert result.ok is False
    assert result.integrity != "ok"


def test_verify_backup_archivo_truncado(tmp_path: Path) -> None:
    source = tmp_path / "origen.db"
    _make_source_db(source)
    data = source.read_bytes()
    truncated = tmp_path / "truncado.db"
    truncated.write_bytes(data[: len(data) // 2])

    result = verify_backup(truncated)

    assert result.ok is False


def test_create_backup_excluye_transaccion_no_confirmada(tmp_path: Path) -> None:
    source = tmp_path / "Mis Respaldos ñ" / "origen.db"
    source.parent.mkdir(parents=True)
    _make_source_db(source)

    # Otra conexión con una transacción abierta, sin confirmar.
    writer = sqlite3.connect(str(source), timeout=5)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute("INSERT INTO productos (nombre) VALUES ('no-confirmado')")

    try:
        destination = tmp_path / "Mis Respaldos ñ" / "respaldo-1.db"
        receipt = create_backup(source, destination)

        assert receipt.verification.ok is True
        assert receipt.verification.integrity == "ok"
        assert receipt.created_at.tzinfo is not None
        assert receipt.created_at.utcoffset() == timedelta(0)
        assert receipt.created_at.astimezone(UTC) == receipt.created_at

        check = sqlite3.connect(str(destination))
        try:
            names = {row[0] for row in check.execute("SELECT nombre FROM productos")}
        finally:
            check.close()
        assert names == {"confirmado-1", "confirmado-2"}
        assert "no-confirmado" not in names

        # No debe quedar archivo .partial tras el éxito.
        assert not destination.with_name(destination.name + ".partial").exists()
    finally:
        writer.rollback()
        writer.close()


def test_create_backup_destino_existente_no_se_sobrescribe(tmp_path: Path) -> None:
    source = tmp_path / "origen.db"
    _make_source_db(source)
    destination = tmp_path / "respaldo.db"
    create_backup(source, destination)
    original_hash = verify_backup(destination).sha256

    with pytest.raises(DestinationExistsError):
        create_backup(source, destination)

    assert verify_backup(destination).sha256 == original_hash
    assert not destination.with_name(destination.name + ".partial").exists()


def test_create_backup_de_archivo_corrupto_falla_sin_dejar_parcial(tmp_path: Path) -> None:
    source = tmp_path / "corrupto.db"
    source.write_bytes(b"no es sqlite" * 20)
    destination = tmp_path / "respaldo.db"

    with pytest.raises((BackupError, sqlite3.Error)):
        create_backup(source, destination)

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".partial").exists()


def test_default_backup_name() -> None:
    import datetime as dt

    now = dt.datetime(2026, 9, 26, 14, 5, 30)
    assert default_backup_name(now) == "sistemashn-20260926-140530.db"
