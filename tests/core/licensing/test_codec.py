"""Pruebas de codificación canónica y firma Ed25519 genérica (T1.4)."""

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sistemashn.core.licensing.codec import (
    FormatError,
    SignatureError,
    UnknownKeyError,
    b64url_decode,
    b64url_encode,
    canonical_json,
    sign,
    verify_signed,
)

PREFIX = "TEST1"


def _public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


@pytest.fixture
def keypair():
    priv = Ed25519PrivateKey.generate()
    return priv, {"k1": _public_bytes(priv)}


def test_canonical_json_ordena_claves_y_es_compacto() -> None:
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b == b'{"a":2,"b":1}'


def test_canonical_json_preserva_acentos_sin_escapar() -> None:
    assert "ñ".encode() in canonical_json({"x": "ñ"})


def test_b64url_ida_y_vuelta_sin_relleno() -> None:
    data = b"\x00\x01\xff\xfe hola"
    texto = b64url_encode(data)
    assert "=" not in texto
    assert b64url_decode(texto) == data


def test_sign_y_verify_signed_ok(keypair) -> None:
    priv, public_keys = keypair
    payload = {"key_id": "k1", "n": 42}
    texto = sign(priv, PREFIX, payload)
    resultado = verify_signed(texto, PREFIX, public_keys)
    assert resultado == payload


def test_verify_signed_detecta_byte_alterado_en_payload(keypair) -> None:
    priv, public_keys = keypair
    payload = {"key_id": "k1", "n": 42}
    firmado = sign(priv, PREFIX, payload)
    _, payload_b64, sig_b64 = firmado.split(".")
    payload_bytes = bytearray(b64url_decode(payload_b64))
    payload_bytes[-2] ^= 0xFF  # altera un byte del JSON (dentro del número)
    payload_alterado_b64 = b64url_encode(bytes(payload_bytes))
    texto = f"{PREFIX}.{payload_alterado_b64}.{sig_b64}"
    with pytest.raises((SignatureError, FormatError)):
        verify_signed(texto, PREFIX, public_keys)


def test_verify_signed_detecta_byte_alterado_en_firma(keypair) -> None:
    priv, public_keys = keypair
    payload = {"key_id": "k1", "n": 42}
    firmado = sign(priv, PREFIX, payload)
    _, payload_b64, sig_b64 = firmado.split(".")
    sig_bytes = bytearray(b64url_decode(sig_b64))
    sig_bytes[0] ^= 0xFF
    sig_alterada_b64 = b64url_encode(bytes(sig_bytes))
    texto = f"{PREFIX}.{payload_b64}.{sig_alterada_b64}"
    with pytest.raises(SignatureError):
        verify_signed(texto, PREFIX, public_keys)


def test_verify_signed_rechaza_otra_clave(keypair) -> None:
    priv, _ = keypair
    otra_priv = Ed25519PrivateKey.generate()
    public_keys = {"k1": _public_bytes(otra_priv)}
    payload = {"key_id": "k1", "n": 1}
    texto = sign(priv, PREFIX, payload)
    with pytest.raises(SignatureError):
        verify_signed(texto, PREFIX, public_keys)


def test_verify_signed_rechaza_key_id_desconocido(keypair) -> None:
    priv, _ = keypair
    payload = {"key_id": "no-existe", "n": 1}
    texto = sign(priv, PREFIX, payload)
    with pytest.raises(UnknownKeyError):
        verify_signed(texto, PREFIX, {"k1": b"x" * 32})


def test_verify_signed_rechaza_prefijo_distinto(keypair) -> None:
    priv, public_keys = keypair
    payload = {"key_id": "k1", "n": 1}
    texto = "OTRO." + sign(priv, PREFIX, payload).split(".", 1)[1]
    with pytest.raises(FormatError):
        verify_signed(texto, PREFIX, public_keys)


def test_verify_signed_rechaza_formato_con_partes_de_mas(keypair) -> None:
    priv, public_keys = keypair
    payload = {"key_id": "k1", "n": 1}
    texto = sign(priv, PREFIX, payload) + ".extra"
    with pytest.raises(FormatError):
        verify_signed(texto, PREFIX, public_keys)


def test_verify_signed_rechaza_payload_no_json(keypair) -> None:
    _, public_keys = keypair
    texto = f"{PREFIX}.{b64url_encode(b'no es json')}.{b64url_encode(b'firma')}"
    with pytest.raises(FormatError):
        verify_signed(texto, PREFIX, public_keys)


def test_verify_signed_rechaza_payload_que_no_es_objeto(keypair) -> None:
    priv, public_keys = keypair
    payload_bytes = json.dumps([1, 2, 3]).encode("utf-8")
    firma = priv.sign(payload_bytes)
    texto = f"{PREFIX}.{b64url_encode(payload_bytes)}.{b64url_encode(firma)}"
    with pytest.raises(FormatError):
        verify_signed(texto, PREFIX, public_keys)


def test_firma_cubre_el_prefijo(keypair) -> None:
    """Un texto firmado para un propósito no se acepta reetiquetado con otro prefijo."""
    priv, public_keys = keypair
    texto = sign(priv, "SHNREC1", {"key_id": "k1", "n": 1})
    reetiquetado = "SHN1." + texto.split(".", 1)[1]
    with pytest.raises(SignatureError):
        verify_signed(reetiquetado, "SHN1", public_keys)
