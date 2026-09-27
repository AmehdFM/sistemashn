"""Pruebas de firma Ed25519 de paquetes de actualización (T6.2)."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sistemashn.core.licensing.codec import b64url_encode
from sistemashn.core.operations.probe_update import InvalidPackageError
from sistemashn.core.updater.package import (
    InvalidSignatureError,
    apply_signed_update,
    manifest_signing_bytes,
    verify_signature,
)

pytestmark = pytest.mark.usefixtures("probe_migrations")

KEY_ID = "test-key"
_PRIVATE_KEY = Ed25519PrivateKey.generate()
_PUBLIC_KEYS = {KEY_ID: _PRIVATE_KEY.public_key().public_bytes_raw()}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sign_manifest(manifest: dict, *, key: Ed25519PrivateKey = _PRIVATE_KEY) -> dict:
    manifest = dict(manifest)
    manifest["key_id"] = KEY_ID
    signature = key.sign(manifest_signing_bytes(manifest))
    manifest["signature"] = b64url_encode(signature)
    return manifest


def _build_zip(
    zip_path: Path,
    *,
    payload: dict[str, bytes],
    version: str = "0.2.0",
    min_from_version: str = "0.1.0",
    schema_revision: str = "0002",
    sign: bool = True,
    manifest_overrides: dict | None = None,
) -> Path:
    files_entry = {name: _sha256(data) for name, data in payload.items()}
    manifest = {
        "format": 1,
        "version": version,
        "min_from_version": min_from_version,
        "schema_revision": schema_revision,
        "files": files_entry,
    }
    if sign:
        manifest = _sign_manifest(manifest)
    if manifest_overrides:
        manifest.update(manifest_overrides)

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for name, data in payload.items():
            zf.writestr(f"payload/{name}", data)
    return zip_path


def _make_installation(base: Path, *, version: str = "0.1.0") -> Path:
    installation = base / "app"
    installation.mkdir(parents=True)
    (installation / "app.txt").write_text("original", encoding="utf-8")
    (installation / "VERSION").write_text(version, encoding="utf-8")
    return installation


def _make_db(base: Path) -> Path:
    from sistemashn.core.db import migrate

    db_path = base / "base.db"
    migrate.upgrade(db_path, "0001")
    return db_path


def test_verify_signature_ok(tmp_path: Path) -> None:
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"})

    verify_signature(zip_path, _PUBLIC_KEYS)


def test_verify_signature_ausente(tmp_path: Path) -> None:
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"}, sign=False)

    with pytest.raises(InvalidSignatureError):
        verify_signature(zip_path, _PUBLIC_KEYS)


def test_verify_signature_key_id_desconocido(tmp_path: Path) -> None:
    otra_clave = Ed25519PrivateKey.generate()
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"}, sign=False)
    # Firma con una clave que no está en el diccionario de claves conocidas.
    with zipfile.ZipFile(zip_path) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    manifest = _sign_manifest(manifest, key=otra_clave)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("payload/app.txt", b"nuevo")

    with pytest.raises(InvalidSignatureError):
        verify_signature(zip_path, _PUBLIC_KEYS)


def test_verify_signature_manifest_alterado_tras_firmar(tmp_path: Path) -> None:
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"})
    with zipfile.ZipFile(zip_path) as zf:
        manifest = json.loads(zf.read("manifest.json"))
    manifest["version"] = "9.9.9"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("payload/app.txt", b"nuevo")

    with pytest.raises(InvalidSignatureError):
        verify_signature(zip_path, _PUBLIC_KEYS)


def test_verify_signature_paquete_corrupto(tmp_path: Path) -> None:
    bad_zip = tmp_path / "roto.zip"
    bad_zip.write_bytes(b"no es un zip")

    with pytest.raises(InvalidPackageError):
        verify_signature(bad_zip, _PUBLIC_KEYS)


def test_apply_signed_update_firma_invalida_no_toca_disco(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "work"
    before_version = (installation / "VERSION").read_text(encoding="utf-8")
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"}, sign=False)

    with pytest.raises(InvalidSignatureError):
        apply_signed_update(zip_path, installation, db_path, work_dir, public_keys=_PUBLIC_KEYS)

    assert (installation / "VERSION").read_text(encoding="utf-8") == before_version
    assert not (work_dir / "update-log.jsonl").exists()


def test_apply_signed_update_firma_valida_aplica(tmp_path: Path) -> None:
    installation = _make_installation(tmp_path)
    db_path = _make_db(tmp_path)
    work_dir = tmp_path / "work"
    zip_path = _build_zip(tmp_path / "update.zip", payload={"app.txt": b"nuevo"})

    result = apply_signed_update(
        zip_path, installation, db_path, work_dir, public_keys=_PUBLIC_KEYS
    )

    assert result.ok is True
    assert (installation / "app.txt").read_text(encoding="utf-8") == "nuevo"
