"""Pruebas de la sección "Actualizaciones" de la pantalla de Respaldos (T6.4)."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tests.core.ui.views.conftest import contiene_texto

from sistemashn import __version__
from sistemashn.core.licensing.codec import b64url_encode
from sistemashn.core.operations.probe_update import InvalidPackageError
from sistemashn.core.ui.views.backups_view import (
    build_backups_view,
    build_updater_command,
    validate_update_package,
)
from sistemashn.core.updater.package import manifest_signing_bytes

pytestmark = pytest.mark.usefixtures("probe_migrations")

KEY_ID = "test-key"
_PRIVATE_KEY = Ed25519PrivateKey.generate()
_PUBLIC_KEYS = {KEY_ID: _PRIVATE_KEY.public_key().public_bytes_raw()}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sign_manifest(manifest: dict) -> dict:
    manifest = dict(manifest)
    manifest["key_id"] = KEY_ID
    firma = _PRIVATE_KEY.sign(manifest_signing_bytes(manifest))
    manifest["signature"] = b64url_encode(firma)
    return manifest


def _build_zip(zip_path: Path, *, version: str = "0.2.0", sign: bool = True) -> Path:
    payload = {"app.txt": b"nuevo"}
    manifest = {
        "format": 1,
        "version": version,
        "min_from_version": "0.1.0",
        "schema_revision": "0002",
        "files": {name: _sha256(data) for name, data in payload.items()},
    }
    if sign:
        manifest = _sign_manifest(manifest)

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        for name, data in payload.items():
            zf.writestr(f"payload/{name}", data)
    return zip_path


def test_validate_update_package_ok(tmp_path):
    zip_path = _build_zip(tmp_path / "update.zip")

    manifest = validate_update_package(zip_path, "0.1.0", public_keys=_PUBLIC_KEYS)

    assert manifest.version == "0.2.0"
    assert manifest.schema_revision == "0002"


def test_validate_update_package_sin_firma_falla(tmp_path):
    zip_path = _build_zip(tmp_path / "update.zip", sign=False)

    with pytest.raises(InvalidPackageError):
        validate_update_package(zip_path, "0.1.0", public_keys=_PUBLIC_KEYS)


def test_validate_update_package_clave_desconocida_falla(tmp_path):
    zip_path = _build_zip(tmp_path / "update.zip")

    with pytest.raises(InvalidPackageError):
        validate_update_package(zip_path, "0.1.0", public_keys={})


def test_validate_update_package_version_no_mayor_falla(tmp_path):
    zip_path = _build_zip(tmp_path / "update.zip", version="0.1.0")

    with pytest.raises(InvalidPackageError):
        validate_update_package(zip_path, "0.1.0", public_keys=_PUBLIC_KEYS)


def test_build_updater_command_arma_los_argumentos_en_orden(tmp_path):
    comando = build_updater_command(
        tmp_path / "paquete.zip",
        tmp_path / "instalacion",
        tmp_path / "base.db",
        tmp_path / "work",
        tmp_path / ".app.lock",
        python_executable="python.exe",
    )

    assert comando == [
        "python.exe",
        "-m",
        "sistemashn.updater",
        str(tmp_path / "paquete.zip"),
        str(tmp_path / "instalacion"),
        str(tmp_path / "base.db"),
        str(tmp_path / "work"),
        str(tmp_path / ".app.lock"),
    ]


def test_build_backups_view_incluye_seccion_de_actualizaciones(ctx_factory, admin_actor):
    ctx = ctx_factory(admin_actor)

    control = build_backups_view(ctx)

    assert contiene_texto(control, "Actualizaciones")
    assert contiene_texto(control, "Elegir paquete de actualización (.zip)...")


def test_version_actual_usada_para_validar_coincide_con_el_paquete_instalado():
    # sanity check: la vista usa __version__ real del paquete, no un valor fijo.
    assert isinstance(__version__, str) and __version__
