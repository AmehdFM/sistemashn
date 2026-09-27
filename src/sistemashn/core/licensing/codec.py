"""Codificación canónica y firma Ed25519 reutilizable (licencias, recuperación, actualizaciones).

Formato general de un texto firmado: `<prefijo>.<payload_b64url>.<firma_b64url>`. El
payload es un objeto JSON canónico que siempre incluye `key_id` para escoger la clave
pública que verifica la firma.
"""

import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class CodecError(Exception):
    """Base de errores al decodificar o verificar un texto firmado."""


class FormatError(CodecError):
    """El texto no tiene el formato `<prefijo>.<payload_b64url>.<firma_b64url>` esperado."""


class SignatureError(CodecError):
    """La firma no corresponde al payload con la clave pública indicada."""


class UnknownKeyError(CodecError):
    """El `key_id` del payload no está entre las claves públicas conocidas."""


def canonical_json(obj: dict) -> bytes:
    """Serializa `obj` de forma canónica y determinista: claves ordenadas, JSON compacto, UTF-8."""
    texto = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return texto.encode("utf-8")


def b64url_encode(data: bytes) -> str:
    """Codifica en base64 URL-safe sin relleno (`=`)."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(text: str) -> bytes:
    """Decodifica base64 URL-safe, restaurando el relleno omitido al codificar."""
    relleno = "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(text + relleno)
    except (ValueError, TypeError) as exc:
        raise FormatError(f"base64url inválido: {exc}") from exc


def _signing_input(prefix: str, payload_b64: str) -> bytes:
    # La firma cubre también el prefijo: un texto firmado para un propósito (licencia,
    # recuperación, actualización) no puede reetiquetarse para otro.
    return f"{prefix}.{payload_b64}".encode("ascii")


def sign(private_key: Ed25519PrivateKey, prefix: str, payload: dict) -> str:
    """Firma `payload` (JSON canónico) con Ed25519; retorna `<prefix>.<payload>.<firma>`."""
    payload_b64 = b64url_encode(canonical_json(payload))
    firma = private_key.sign(_signing_input(prefix, payload_b64))
    return f"{prefix}.{payload_b64}.{b64url_encode(firma)}"


def verify_signed(text: str, prefix: str, public_keys: dict[str, bytes]) -> dict:
    """Verifica un texto `<prefix>.<payload_b64url>.<firma_b64url>` y retorna el payload.

    Lanza `FormatError` si el texto no tiene el formato esperado o el payload no es un
    objeto JSON válido, `UnknownKeyError` si `key_id` no está en `public_keys`, y
    `SignatureError` si la firma no corresponde al payload con esa clave pública.
    """
    partes = text.split(".")
    if len(partes) != 3 or partes[0] != prefix:
        raise FormatError(f"formato inválido, se esperaba el prefijo {prefix!r}")
    _, payload_b64, firma_b64 = partes

    payload_bytes = b64url_decode(payload_b64)
    firma = b64url_decode(firma_b64)

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise FormatError(f"el payload no es JSON válido: {exc}") from exc
    if not isinstance(payload, dict):
        raise FormatError("el payload debe ser un objeto JSON")

    key_id = payload.get("key_id")
    if not isinstance(key_id, str) or key_id not in public_keys:
        raise UnknownKeyError(f"key_id desconocido: {key_id!r}")

    clave_publica = Ed25519PublicKey.from_public_bytes(public_keys[key_id])
    try:
        clave_publica.verify(firma, _signing_input(prefix, payload_b64))
    except InvalidSignature as exc:
        raise SignatureError("la firma no corresponde al payload") from exc

    return payload
