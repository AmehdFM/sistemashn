"""Formato y verificación de licencias offline y códigos de solicitud (T1.4, spec §5).

Licencia perpetua: `SHN1.<payload_b64url>.<firma_b64url>`. El payload incluye
`license_id, vertical, business_name, installation_id, fingerprint, edition, issued_at,
format, key_id`. El reloj no influye en la validez: la licencia es perpetua.

Código de solicitud (sin firmar, lo genera la máquina del cliente):
`SHNREQ1.<payload_b64url>` con `installation_id, vertical, fingerprint, app_version`.
"""

import json
from dataclasses import dataclass

from sistemashn.core.errors import SistemasHNError
from sistemashn.core.licensing.codec import (
    FormatError,
    SignatureError,
    UnknownKeyError,
    b64url_decode,
    b64url_encode,
    canonical_json,
    verify_signed,
)

LICENSE_PREFIX = "SHN1"
REQUEST_PREFIX = "SHNREQ1"

_REQUEST_FIELDS = {"installation_id", "vertical", "fingerprint", "app_version"}
_LICENSE_FIELDS = {
    "license_id",
    "vertical",
    "business_name",
    "installation_id",
    "fingerprint",
    "edition",
    "issued_at",
    "format",
}


class LicenseError(SistemasHNError):
    """Error al procesar o verificar una licencia.

    `reason` clasifica el motivo: `formato`, `firma`, `vertical`, `maquina`,
    `instalacion` o `clave`.
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        super().__init__(message or reason)
        self.reason = reason


@dataclass(frozen=True)
class LicenseInfo:
    """Datos verificados de una licencia instalada."""

    license_id: str
    vertical: str
    business_name: str
    installation_id: str
    fingerprint: str
    edition: str
    issued_at: str
    raw_text: str


def build_request_code(
    installation_id: str, vertical: str, fingerprint: str, app_version: str
) -> str:
    """Construye `SHNREQ1.<payload_b64url>` (sin firma) para pedirle licencia al vendedor."""
    payload = {
        "installation_id": installation_id,
        "vertical": vertical,
        "fingerprint": fingerprint,
        "app_version": app_version,
    }
    return f"{REQUEST_PREFIX}.{b64url_encode(canonical_json(payload))}"


def parse_request_code(text: str) -> dict:
    """Recupera el payload de un código de solicitud `SHNREQ1...`.

    Lanza `LicenseError("formato")` si el texto no tiene el formato esperado.
    """
    prefijo, separador, payload_b64 = text.partition(".")
    if separador != "." or prefijo != REQUEST_PREFIX or not payload_b64:
        raise LicenseError("formato", f"código de solicitud inválido: {text!r}")
    try:
        payload_bytes = b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (FormatError, ValueError, UnicodeDecodeError) as exc:
        raise LicenseError("formato", f"código de solicitud inválido: {exc}") from exc
    if not isinstance(payload, dict) or not _REQUEST_FIELDS.issubset(payload):
        raise LicenseError("formato", "código de solicitud incompleto")
    return payload


def verify_license(
    text: str,
    *,
    expected_vertical: str,
    installation_id: str,
    fingerprint: str,
    public_keys: dict[str, bytes],
) -> LicenseInfo:
    """Verifica una licencia `SHN1...` y la valida contra la instalación actual.

    El reloj no participa: la licencia es perpetua y no expira. Lanza `LicenseError`
    con el motivo correspondiente (`formato`, `firma`, `clave`, `vertical`,
    `instalacion` o `maquina`) si algo no coincide.
    """
    try:
        payload = verify_signed(text, LICENSE_PREFIX, public_keys)
    except UnknownKeyError as exc:
        raise LicenseError("clave", str(exc)) from exc
    except SignatureError as exc:
        raise LicenseError("firma", str(exc)) from exc
    except FormatError as exc:
        raise LicenseError("formato", str(exc)) from exc

    if not _LICENSE_FIELDS.issubset(payload):
        raise LicenseError("formato", "licencia incompleta")

    if payload["vertical"] != expected_vertical:
        raise LicenseError("vertical", "la licencia no corresponde a este producto")
    if payload["installation_id"] != installation_id:
        raise LicenseError("instalacion", "la licencia no corresponde a esta instalación")
    if payload["fingerprint"] != fingerprint:
        raise LicenseError("maquina", "la licencia no corresponde a esta máquina")

    return LicenseInfo(
        license_id=payload["license_id"],
        vertical=payload["vertical"],
        business_name=payload["business_name"],
        installation_id=payload["installation_id"],
        fingerprint=payload["fingerprint"],
        edition=payload["edition"],
        issued_at=payload["issued_at"],
        raw_text=text,
    )
