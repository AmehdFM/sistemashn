import hashlib
import json
import sqlite3
import zipfile

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import URL

from sistemashn.core.operations.contracts import UpdateError
from sistemashn.core.operations.probe_update import apply_probe_update


def _fixture(tmp_path):
    installation = tmp_path / "Instalación José"
    data = tmp_path / "Datos José"
    installation.mkdir()
    data.mkdir()
    (installation / "app.bin").write_bytes(b"old app")
    (installation / "version.json").write_text('{"version":"0.0.1"}', encoding="utf-8")
    db = data / "probe.sqlite3"
    config = Config(str(__import__("pathlib").Path(__file__).resolve().parents[2] / "alembic.ini"))
    url = URL.create("sqlite", database=str(db)).render_as_string(hide_password=False)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "0001")
    with sqlite3.connect(db) as con:
        con.execute("INSERT INTO probe_records (id, value) VALUES (7, 'conservado')")
    return installation, data


def _package(tmp_path, *, bad_hash=False, extra=False):
    package = tmp_path / "update.zip"
    app = b"new app"
    digest = "bad" if bad_hash else hashlib.sha256(app).hexdigest()
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"format": 1, "from_version": "0.0.1", "to_version": "0.0.2", "app_sha256": digest}))
        archive.writestr("app.bin", app)
        if extra:
            archive.writestr("extra", b"unsafe")
    return package


@pytest.mark.parametrize("invalid", ["bad_hash", "extra"])
def test_invalid_package_does_not_change_installation(tmp_path, invalid):
    installation, data = _fixture(tmp_path)
    package = _package(tmp_path, **{invalid: True})
    with pytest.raises(UpdateError):
        apply_probe_update(package, installation, data)
    assert (installation / "app.bin").read_bytes() == b"old app"
    with sqlite3.connect(data / "probe.sqlite3") as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("0001",)


@pytest.mark.parametrize("failure", ["migration", "staged_start", "published_start"])
def test_failed_update_recovers_binary_version_and_database(tmp_path, monkeypatch, failure):
    from sistemashn.core.operations import probe_update

    installation, data = _fixture(tmp_path)
    package = _package(tmp_path)
    if failure == "migration":
        monkeypatch.setattr(probe_update, "_migrate", lambda _: (_ for _ in ()).throw(RuntimeError("migration failed")))
    if failure in ("staged_start", "published_start"):
        def failed_start(app, data_dir):
            if failure == "staged_start" or data_dir == data:
                raise RuntimeError("startup failed")
        monkeypatch.setattr(probe_update, "_startup_probe", failed_start)
    with pytest.raises(UpdateError):
        apply_probe_update(package, installation, data)
    assert (installation / "app.bin").read_bytes() == b"old app"
    assert json.loads((installation / "version.json").read_text())["version"] == "0.0.1"
    with sqlite3.connect(data / "probe.sqlite3") as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("0001",)
        assert db.execute("SELECT value FROM probe_records WHERE id=7").fetchone() == ("conservado",)
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_successful_update_preserves_record(tmp_path):
    installation, data = _fixture(tmp_path)
    result = apply_probe_update(_package(tmp_path), installation, data)
    assert result.installed_version == "0.0.2"
    assert (installation / "app.bin").read_bytes() == b"new app"
    with sqlite3.connect(data / "probe.sqlite3") as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("0002",)
        assert db.execute("SELECT value, note FROM probe_records WHERE id=7").fetchone() == ("conservado", "")
