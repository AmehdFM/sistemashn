"""Pruebas de formato de licencia y código de solicitud (T1.4, spec §5)."""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from sistemashn.core.licensing.codec import b64url_decode, b64url_encode, sign
from sistemashn.core.licensing.license import (
    LICENSE_PREFIX,
    LicenseError,
    LicenseInfo,
    build_request_code,
    parse_request_code,
    verify_license,
)

INSTALLATION_ID = "11111111-1111-1111-1111-111111111111"
VERTICAL = "repuestos"
FINGERPRINT = "f" * 64
KEY_ID = "dev-1"


def _public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


@pytest.fixture
def keypair():
    priv = Ed25519PrivateKey.generate()
    return priv, {KEY_ID: _public_bytes(priv)}


def _license_payload(**overrides) -> dict:
    payload = {
        "license_id": "lic-1",
        "vertical": VERTICAL,
        "business_name": "Repuestos Ejemplo",
        "installation_id": INSTALLATION_ID,
        "fingerprint": FINGERPRINT,
        "edition": "perpetua",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "format": 1,
        "key_id": KEY_ID,
    }
    payload.update(overrides)
    return payload


def _make_license(priv, **overrides) -> str:
    return sign(priv, LICENSE_PREFIX, _license_payload(**overrides))


def test_request_code_ida_y_vuelta() -> None:
    texto = build_request_code(INSTALLATION_ID, VERTICAL, FINGERPRINT, "0.1.0")
    payload = parse_request_code(texto)
    assert payload == {
        "installation_id": INSTALLATION_ID,
        "vertical": VERTICAL,
        "fingerprint": FINGERPRINT,
        "app_version": "0.1.0",
    }


def test_parse_request_code_rechaza_prefijo_incorrecto() -> None:
    with pytest.raises(LicenseError) as excinfo:
        parse_request_code("OTRO.abc")
    assert excinfo.value.reason == "formato"


def test_parse_request_code_rechaza_payload_incompleto() -> None:
    from sistemashn.core.licensing.codec import canonical_json

    incompleto = b64url_encode(canonical_json({"installation_id": "x"}))
    with pytest.raises(LicenseError) as excinfo:
        parse_request_code(f"SHNREQ1.{incompleto}")
    assert excinfo.value.reason == "formato"


def test_verify_license_ok(keypair) -> None:
    priv, public_keys = keypair
    texto = _make_license(priv)
    info = verify_license(
        texto,
        expected_vertical=VERTICAL,
        installation_id=INSTALLATION_ID,
        fingerprint=FINGERPRINT,
        public_keys=public_keys,
    )
    assert isinstance(info, LicenseInfo)
    assert info.license_id == "lic-1"
    assert info.raw_text == texto


def test_verify_license_byte_alterado_en_payload(keypair) -> None:
    priv, public_keys = keypair
    texto = _make_license(priv)
    prefijo, payload_b64, sig_b64 = texto.split(".")
    payload_bytes = bytearray(b64url_decode(payload_b64))
    payload_bytes[0] ^= 0xFF
    texto_alterado = f"{prefijo}.{b64url_encode(bytes(payload_bytes))}.{sig_b64}"
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto_alterado,
            expected_vertical=VERTICAL,
            installation_id=INSTALLATION_ID,
            fingerprint=FINGERPRINT,
            public_keys=public_keys,
        )
    assert excinfo.value.reason in ("firma", "formato")


def test_verify_license_byte_alterado_en_firma(keypair) -> None:
    priv, public_keys = keypair
    texto = _make_license(priv)
    prefijo, payload_b64, sig_b64 = texto.split(".")
    sig_bytes = bytearray(b64url_decode(sig_b64))
    sig_bytes[0] ^= 0xFF
    texto_alterado = f"{prefijo}.{payload_b64}.{b64url_encode(bytes(sig_bytes))}"
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto_alterado,
            expected_vertical=VERTICAL,
            installation_id=INSTALLATION_ID,
            fingerprint=FINGERPRINT,
            public_keys=public_keys,
        )
    assert excinfo.value.reason == "firma"


def test_verify_license_rechaza_otra_clave(keypair) -> None:
    priv, _ = keypair
    otra_priv = Ed25519PrivateKey.generate()
    texto = _make_license(priv)
    public_keys = {KEY_ID: _public_bytes(otra_priv)}
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto,
            expected_vertical=VERTICAL,
            installation_id=INSTALLATION_ID,
            fingerprint=FINGERPRINT,
            public_keys=public_keys,
        )
    assert excinfo.value.reason == "firma"


def test_verify_license_rechaza_key_id_desconocido(keypair) -> None:
    priv, _ = keypair
    texto = _make_license(priv)
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto,
            expected_vertical=VERTICAL,
            installation_id=INSTALLATION_ID,
            fingerprint=FINGERPRINT,
            public_keys={},
        )
    assert excinfo.value.reason == "clave"


def test_verify_license_rechaza_otra_huella(keypair) -> None:
    priv, public_keys = keypair
    texto = _make_license(priv)
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto,
            expected_vertical=VERTICAL,
            installation_id=INSTALLATION_ID,
            fingerprint="0" * 64,
            public_keys=public_keys,
        )
    assert excinfo.value.reason == "maquina"


def test_verify_license_rechaza_otra_instalacion(keypair) -> None:
    priv, public_keys = keypair
    texto = _make_license(priv)
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto,
            expected_vertical=VERTICAL,
            installation_id="22222222-2222-2222-2222-222222222222",
            fingerprint=FINGERPRINT,
            public_keys=public_keys,
        )
    assert excinfo.value.reason == "instalacion"


def test_verify_license_rechaza_otra_vertical(keypair) -> None:
    priv, public_keys = keypair
    texto = _make_license(priv)
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto,
            expected_vertical="ferreteria",
            installation_id=INSTALLATION_ID,
            fingerprint=FINGERPRINT,
            public_keys=public_keys,
        )
    assert excinfo.value.reason == "vertical"


def test_verify_license_rechaza_payload_incompleto(keypair) -> None:
    priv, public_keys = keypair
    payload = _license_payload()
    del payload["business_name"]
    texto = sign(priv, LICENSE_PREFIX, payload)
    with pytest.raises(LicenseError) as excinfo:
        verify_license(
            texto,
            expected_vertical=VERTICAL,
            installation_id=INSTALLATION_ID,
            fingerprint=FINGERPRINT,
            public_keys=public_keys,
        )
    assert excinfo.value.reason == "formato"
