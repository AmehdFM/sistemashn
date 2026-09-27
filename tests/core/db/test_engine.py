"""Pruebas de sistemashn.core.db.engine (ADR-002: PRAGMAs, rutas, data_dir)."""

from pathlib import Path

import pytest
from sqlalchemy import text

from sistemashn.core.db.engine import create_engine_for_path, data_dir


@pytest.fixture
def engine(tmp_path):
    ruta = tmp_path / "carpeta con espacios ñandú" / "base.db"
    eng = create_engine_for_path(ruta)
    yield eng
    eng.dispose()


def test_crea_carpeta_padre_con_espacios_y_acentos(tmp_path) -> None:
    ruta = tmp_path / "carpeta con espacios ñandú" / "sub" / "base.db"
    eng = create_engine_for_path(ruta)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        assert ruta.parent.is_dir()
        assert ruta.exists()
    finally:
        eng.dispose()


def test_pragmas_en_cada_conexion(engine) -> None:
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA synchronous")).scalar() == 2  # FULL
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
    # segunda conexión también debe llevar los PRAGMAs
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_busy_timeout_personalizado(tmp_path) -> None:
    ruta = tmp_path / "otra.db"
    eng = create_engine_for_path(ruta, busy_timeout_ms=250)
    try:
        with eng.connect() as conn:
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 250
    finally:
        eng.dispose()


def test_data_dir_usa_env_var(monkeypatch, tmp_path) -> None:
    destino = tmp_path / "datos-custom"
    monkeypatch.setenv("SISTEMASHN_DATA_DIR", str(destino))
    resultado = data_dir("repuestos")
    assert Path(resultado) == destino


def test_data_dir_sin_env_var_usa_localappdata(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("SISTEMASHN_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    resultado = data_dir("repuestos")
    assert Path(resultado) == tmp_path / "SistemasHN" / "repuestos"
