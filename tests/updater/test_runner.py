"""Pruebas del proceso `updater`: espera de cierre y aplicación con reintento (T6.3)."""

import hashlib
import json
import os
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sistemashn.core.licensing.codec import b64url_encode
from sistemashn.core.updater.package import manifest_signing_bytes
from sistemashn.updater.runner import run_update, wait_for_app_exit

pytestmark = pytest.mark.usefixtures("probe_migrations")

KEY_ID = "test-key"
_PRIVATE_KEY = Ed25519PrivateKey.generate()
_PUBLIC_KEYS = {KEY_ID: _PRIVATE_KEY.public_key().public_bytes_raw()}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_signed_zip(
    zip_path: Path, *, payload: dict[str, bytes], version: str = "0.2.0", schema_revision="0002"
) -> Path:
    manifest = {
        "format": 1,
        "version": version,
        "min_from_version": "0.1.0",
        "schema_revision": schema_revision,
        "files": {name: _sha256(data) for name, data in payload.items()},
        "key_id": KEY_ID,
    }
    firma = _PRIVATE_KEY.sign(manifest_signing_bytes(manifest))
    manifest["signature"] = b64url_encode(firma)

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for name, data in payload.items():
            zf.writestr(f"payload/{name}", data)
    return zip_path


def _make_installation(base: Path) -> Path:
    installation = base / "app"
    installation.mkdir(parents=True)
    (installation / "app.txt").write_text("original", encoding="utf-8")
    (installation / "VERSION").write_text("0.1.0", encoding="utf-8")
    return installation


def _make_db(base: Path) -> Path:
    from sistemashn.core.db import migrate

    db_path = base / "base.db"
    migrate.upgrade(db_path, "0001")
    return db_path


# --------------------------------------------------------------------------
# wait_for_app_exit
# --------------------------------------------------------------------------


def test_wait_for_app_exit_sin_lock_file_retorna_true_de_inmediato(tmp_path: Path) -> None:
    lock_file = tmp_path / ".app.lock"

    assert wait_for_app_exit(lock_file) is True


def test_wait_for_app_exit_pid_inexistente_retorna_true(tmp_path: Path) -> None:
    lock_file = tmp_path / ".app.lock"
    # Un PID casi con seguridad inexistente en este sistema.
    lock_file.write_text("999999999", encoding="utf-8")

    assert wait_for_app_exit(lock_file, sleep=lambda _s: None) is True


def test_wait_for_app_exit_proceso_vivo_agota_tiempo_y_retorna_false(tmp_path: Path) -> None:
    lock_file = tmp_path / ".app.lock"
    lock_file.write_text(str(os.getpid()), encoding="utf-8")  # nuestro propio proceso: vivo

    tiempos = iter([0.0, 1.0, 2.0, 3.0, 31.0])
    dormidas = []

    resultado = wait_for_app_exit(
        lock_file,
        max_wait_seconds=30.0,
        poll_interval=1.0,
        sleep=dormidas.append,
        now=lambda: next(tiempos),
    )

    assert resultado is False
    assert dormidas  # sondeó al menos una vez sin dormir de verdad


# --------------------------------------------------------------------------
# run_update
# --------------------------------------------------------------------------


def test_run_update_app_ya_cerrada_aplica(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "work"
    lock_file = tmp_path / ".app.lock"  # no existe: cierre limpio
    zip_path = _build_signed_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"})

    resultado = run_update(
        zip_path, installation, db_path, work_dir, lock_file, public_keys=_PUBLIC_KEYS
    )

    assert resultado.ok is True
    assert (installation / "app.txt").read_text(encoding="utf-8") == "nuevo"


def test_run_update_app_viva_no_libera_falla_sin_aplicar(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "work"
    lock_file = tmp_path / ".app.lock"
    lock_file.write_text(str(os.getpid()), encoding="utf-8")
    zip_path = _build_signed_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"})

    resultado = run_update(
        zip_path,
        installation,
        db_path,
        work_dir,
        lock_file,
        public_keys=_PUBLIC_KEYS,
        max_wait_seconds=0.0,
    )

    assert resultado.ok is False
    assert "no cerró" in resultado.error
    assert (installation / "app.txt").read_text(encoding="utf-8") == "original"
    assert not (work_dir / "update-log.jsonl").exists()


def test_run_update_reintenta_una_vez_si_falla_y_luego_funciona(
    tmp_path: Path, monkeypatch
) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "work"
    lock_file = tmp_path / ".app.lock"
    zip_path = _build_signed_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"})

    from sistemashn.core.operations.probe_update import UpdateResult
    from sistemashn.updater import runner as runner_module

    llamadas = {"n": 0}
    original = runner_module.apply_signed_update

    def _flaky(*args, **kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return UpdateResult(
                ok=False,
                from_version="0.1.0",
                to_version="0.2.0",
                error="falla simulada",
                rolled_back=True,
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(runner_module, "apply_signed_update", _flaky)

    resultado = run_update(
        zip_path, installation, db_path, work_dir, lock_file, public_keys=_PUBLIC_KEYS
    )

    assert llamadas["n"] == 2
    assert resultado.ok is True
