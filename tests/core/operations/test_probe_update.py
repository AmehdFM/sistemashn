"""Pruebas de actualización local de ensayo por ZIP (T0.4)."""

import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from sistemashn.core.db import migrate
from sistemashn.core.operations.probe_update import (
    InvalidPackageError,
    UpdateManifest,
    apply_probe_update,
    read_manifest,
    validate_package,
)

pytestmark = pytest.mark.usefixtures("probe_migrations")

INSTALLED_VERSION = "0.1.0"
NEW_VERSION = "0.2.0"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_zip(
    zip_path: Path,
    *,
    payload: dict[str, bytes],
    version: str = NEW_VERSION,
    min_from_version: str = "0.1.0",
    schema_revision: str = "0002",
    manifest_overrides: dict | None = None,
    files_overrides: dict | None = None,
    include_manifest: bool = True,
    extra_payload: dict[str, bytes] | None = None,
) -> Path:
    files_entry = {name: _sha256(data) for name, data in payload.items()}
    if files_overrides is not None:
        files_entry.update(files_overrides)
    manifest = {
        "format": 1,
        "version": version,
        "min_from_version": min_from_version,
        "schema_revision": schema_revision,
        "files": files_entry,
    }
    if manifest_overrides:
        manifest.update(manifest_overrides)

    with zipfile.ZipFile(zip_path, "w") as zf:
        if include_manifest:
            zf.writestr("manifest.json", json.dumps(manifest))
        for name, data in payload.items():
            zf.writestr(f"payload/{name}", data)
        if extra_payload:
            for name, data in extra_payload.items():
                zf.writestr(f"payload/{name}", data)
    return zip_path


def _make_installation(base: Path, *, version: str = INSTALLED_VERSION) -> Path:
    installation = base / "instalación con espacios"
    installation.mkdir(parents=True)
    (installation / "app.txt").write_text("contenido-original", encoding="utf-8")
    (installation / "VERSION").write_text(version, encoding="utf-8")
    return installation


def _make_db(base: Path) -> Path:
    db_path = base / "base.db"
    migrate.upgrade(db_path, "0001")
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute("INSERT INTO probe_records (id, value) VALUES (1, 'original')")
        connection.commit()
    finally:
        connection.close()
    return db_path


def _dir_hashes(path: Path) -> dict[str, str]:
    hashes = {}
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            hashes[str(file_path.relative_to(path))] = _sha256(file_path.read_bytes())
    return hashes


def _read_probe_row(db_path: Path) -> tuple[str, str] | None:
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT value, note FROM probe_records WHERE id = 1")
            ).fetchone()
        return (row.value, row.note) if row is not None else None
    finally:
        engine.dispose()


def _read_probe_row_no_note(db_path: Path) -> str | None:
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT value FROM probe_records WHERE id = 1")).fetchone()
        return row.value if row is not None else None
    finally:
        engine.dispose()


# --------------------------------------------------------------------------
# read_manifest / validate_package
# --------------------------------------------------------------------------


def test_read_manifest_ok(tmp_path: Path) -> None:
    payload = {"app.txt": b"contenido-nuevo"}
    zip_path = _build_zip(tmp_path / "update.zip", payload=payload)

    manifest = read_manifest(zip_path)

    assert isinstance(manifest, UpdateManifest)
    assert manifest.format == 1
    assert manifest.version == NEW_VERSION
    assert manifest.schema_revision == "0002"
    assert manifest.files["app.txt"] == _sha256(payload["app.txt"])


def test_validate_package_ok(tmp_path: Path) -> None:
    payload = {"app.txt": b"contenido-nuevo"}
    zip_path = _build_zip(tmp_path / "update.zip", payload=payload)

    manifest = validate_package(zip_path, INSTALLED_VERSION)

    assert manifest.version == NEW_VERSION


def test_validate_package_zip_ilegible(tmp_path: Path) -> None:
    bad_zip = tmp_path / "roto.zip"
    bad_zip.write_bytes(b"esto no es un zip")

    with pytest.raises(InvalidPackageError):
        validate_package(bad_zip, INSTALLED_VERSION)


def test_validate_package_manifest_ausente(tmp_path: Path) -> None:
    zip_path = _build_zip(
        tmp_path / "update.zip", payload={"app.txt": b"x"}, include_manifest=False
    )

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_hash_invalido(tmp_path: Path) -> None:
    zip_path = _build_zip(
        tmp_path / "update.zip",
        payload={"app.txt": b"contenido-nuevo"},
        files_overrides={"app.txt": "0" * 64},
    )

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_archivo_faltante_en_payload(tmp_path: Path) -> None:
    zip_path = _build_zip(
        tmp_path / "update.zip",
        payload={},
        files_overrides={"app.txt": "0" * 64},
    )

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_archivo_extra_en_payload(tmp_path: Path) -> None:
    zip_path = _build_zip(
        tmp_path / "update.zip",
        payload={"app.txt": b"contenido-nuevo"},
        extra_payload={"sobrante.txt": b"no listado"},
    )

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_path_traversal(tmp_path: Path) -> None:
    zip_path = _build_zip(tmp_path / "update.zip", payload={"../evil.txt": b"malo"})

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_ruta_absoluta(tmp_path: Path) -> None:
    zip_path = _build_zip(tmp_path / "update.zip", payload={"/evil.txt": b"malo"})

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_downgrade(tmp_path: Path) -> None:
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"x"}, version="0.0.9")

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_version_igual(tmp_path: Path) -> None:
    zip_path = _build_zip(
        tmp_path / "update.zip", payload={"app.txt": b"x"}, version=INSTALLED_VERSION
    )

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


def test_validate_package_min_from_version_no_cumplida(tmp_path: Path) -> None:
    zip_path = _build_zip(
        tmp_path / "update.zip",
        payload={"app.txt": b"x"},
        min_from_version="0.5.0",
    )

    with pytest.raises(InvalidPackageError):
        validate_package(zip_path, INSTALLED_VERSION)


# --------------------------------------------------------------------------
# apply_probe_update
# --------------------------------------------------------------------------


def test_apply_probe_update_exito(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "trabajo temporal"
    zip_path = _build_zip(
        tmp_path / "update.zip", payload={"app.txt": "contenido-nuevo-ñ".encode()}
    )

    result = apply_probe_update(zip_path, installation, db_path, work_dir)

    assert result.ok is True
    assert result.rolled_back is False
    assert result.from_version == INSTALLED_VERSION
    assert result.to_version == NEW_VERSION
    assert (installation / "VERSION").read_text(encoding="utf-8") == NEW_VERSION
    assert (installation / "app.txt").read_text(encoding="utf-8") == "contenido-nuevo-ñ"
    assert migrate.current_revision(db_path) == "0002"
    assert _read_probe_row(db_path) == ("original", "")

    log_path = work_dir / "update-log.jsonl"
    assert log_path.exists()
    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert lines[-1]["ok"] is True


def test_apply_probe_update_paquete_invalido_no_toca_nada(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "work"
    before_app_hashes = _dir_hashes(installation)
    before_db_hash = _sha256(db_path.read_bytes())

    zip_path = _build_zip(
        tmp_path / "update.zip",
        payload={"app.txt": b"contenido-nuevo"},
        files_overrides={"app.txt": "0" * 64},
    )

    with pytest.raises(InvalidPackageError):
        apply_probe_update(zip_path, installation, db_path, work_dir)

    assert _dir_hashes(installation) == before_app_hashes
    assert _sha256(db_path.read_bytes()) == before_db_hash
    assert not (work_dir / "update-log.jsonl").exists()


def test_apply_probe_update_startup_check_falla_revierte(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "trabajo"
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"contenido-nuevo"})

    def _fallar(_installation: Path, _db_path: Path) -> None:
        raise RuntimeError("la app de prueba no arrancó")

    result = apply_probe_update(zip_path, installation, db_path, work_dir, startup_check=_fallar)

    assert result.ok is False
    assert result.rolled_back is True
    assert result.from_version == INSTALLED_VERSION
    assert result.to_version == NEW_VERSION
    assert "no arrancó" in result.error

    assert (installation / "VERSION").read_text(encoding="utf-8") == INSTALLED_VERSION
    assert (installation / "app.txt").read_text(encoding="utf-8") == "contenido-original"
    assert migrate.current_revision(db_path) == "0001"
    assert _read_probe_row_no_note(db_path) == "original"

    log_path = work_dir / "update-log.jsonl"
    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert lines[-1]["ok"] is False
    assert lines[-1]["error"]


def test_apply_probe_update_migracion_fallida_revierte(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "trabajo"
    zip_path = _build_zip(
        tmp_path / "update.zip",
        payload={"app.txt": b"contenido-nuevo"},
        schema_revision="9999",
    )

    result = apply_probe_update(zip_path, installation, db_path, work_dir)

    assert result.ok is False
    assert result.rolled_back is True

    assert (installation / "VERSION").read_text(encoding="utf-8") == INSTALLED_VERSION
    assert (installation / "app.txt").read_text(encoding="utf-8") == "contenido-original"
    assert migrate.current_revision(db_path) == "0001"
    assert _read_probe_row_no_note(db_path) == "original"

    log_path = work_dir / "update-log.jsonl"
    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert lines[-1]["ok"] is False


def test_apply_probe_update_rutas_con_espacios_y_acentos(tmp_path: Path) -> None:
    base = tmp_path / "raíz de prueba"
    base.mkdir()
    installation = _make_installation(base)
    db_path = _make_db(base)
    work_dir = base / "trabajo temporal ñ"
    zip_path = _build_zip(base / "update.zip", payload={"app.txt": "nuevo-ñ".encode()})

    result = apply_probe_update(zip_path, installation, db_path, work_dir)

    assert result.ok is True
    assert (installation / "app.txt").read_text(encoding="utf-8") == "nuevo-ñ"
