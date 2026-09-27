"""Verificación de firma Ed25519 de un paquete de actualización, previa al contrato ADR-003.

Extiende `core.operations.probe_update` sin modificarlo: `apply_signed_update` exige
una firma válida del `manifest.json` ANTES de delegar en `apply_probe_update`, que
sigue siendo el único responsable de aplicar/revertir cambios en disco.

El manifiesto sigue siendo JSON plano (no el formato de texto envuelto
`<prefijo>.<payload>.<firma>` de `core.licensing.codec.sign`); se firman los bytes
canónicos del propio `manifest.json` con un prefijo de dominio separado
(`_MANIFEST_SIGN_PREFIX`) para que una firma de actualización no pueda reutilizarse
en otro contexto (licencias, recuperación).

Decisión: `key_id` SÍ participa de lo firmado (solo se excluye `signature`). Si
`key_id` no estuviera protegido, alguien podría reetiquetar una firma válida bajo un
`key_id` distinto y confundir qué clave la respalda; al incluirlo, cualquier cambio de
`key_id` invalida la firma.
"""

import json
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from sistemashn.core.licensing.codec import b64url_decode, canonical_json
from sistemashn.core.operations.probe_update import (
    InvalidPackageError,
    UpdateResult,
    apply_probe_update,
)
from sistemashn.core.updater.keys import UPDATE_PUBLIC_KEYS

_MANIFEST_NAME = "manifest.json"
_MANIFEST_SIGN_PREFIX = b"sistemashn-update-v1."


def _default_clock() -> datetime:
    return datetime.now(UTC)


class InvalidSignatureError(InvalidPackageError):
    """La firma del manifiesto de actualización es inválida, ausente o de clave desconocida."""


def manifest_signing_bytes(manifest_dict: dict) -> bytes:
    """Bytes exactos que se firman/verifican: prefijo de dominio + JSON canónico sin `signature`."""
    resto = {clave: valor for clave, valor in manifest_dict.items() if clave != "signature"}
    return _MANIFEST_SIGN_PREFIX + canonical_json(resto)


def _read_raw_manifest(package: Path) -> dict:
    try:
        zf = zipfile.ZipFile(package)
    except (zipfile.BadZipFile, FileNotFoundError, OSError) as exc:
        raise InvalidPackageError(f"ZIP ilegible ({package}): {exc}") from exc

    try:
        try:
            raw = zf.read(_MANIFEST_NAME)
        except KeyError as exc:
            raise InvalidPackageError("manifest.json ausente en el paquete") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise InvalidPackageError(f"manifest.json malformado: {exc}") from exc
        if not isinstance(data, dict):
            raise InvalidPackageError("manifest.json malformado: no es un objeto")
        return data
    finally:
        zf.close()


def verify_signature(package: Path, public_keys: dict[str, bytes] = UPDATE_PUBLIC_KEYS) -> None:
    """Verifica la firma Ed25519 del manifiesto del paquete; lanza `InvalidSignatureError` si falla.

    No lanza nada (retorna `None`) si la firma es válida. No modifica el disco.
    """
    data = _read_raw_manifest(package)

    signature_b64 = data.get("signature")
    key_id = data.get("key_id")
    if not isinstance(signature_b64, str) or not isinstance(key_id, str):
        raise InvalidSignatureError("manifest.json no tiene 'signature'/'key_id' válidos")

    if key_id not in public_keys:
        raise InvalidSignatureError(f"key_id desconocido: {key_id!r}")

    try:
        firma = b64url_decode(signature_b64)
    except Exception as exc:  # base64 inválido
        raise InvalidSignatureError(f"firma con base64url inválido: {exc}") from exc

    clave_publica = Ed25519PublicKey.from_public_bytes(public_keys[key_id])
    try:
        clave_publica.verify(firma, manifest_signing_bytes(data))
    except InvalidSignature as exc:
        raise InvalidSignatureError("la firma del manifiesto no es válida") from exc


def apply_signed_update(
    package: Path,
    installation: Path,
    db_path: Path,
    work_dir: Path,
    *,
    public_keys: dict[str, bytes] = UPDATE_PUBLIC_KEYS,
    startup_check: Callable[[Path, Path], None] | None = None,
    clock: Callable[[], datetime] = _default_clock,
) -> UpdateResult:
    """Verifica la firma del paquete y, solo si es válida, aplica `apply_probe_update`.

    Si la firma no es válida la excepción se propaga sin tocar disco: no se llega a
    respaldar ni a extraer nada.
    """
    verify_signature(package, public_keys)
    return apply_probe_update(
        package, installation, db_path, work_dir, startup_check=startup_check, clock=clock
    )
