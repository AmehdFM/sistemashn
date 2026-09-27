"""Fixtures compartidas para las pruebas del asistente de primer arranque (T1.5)."""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from sistemashn.core.licensing.codec import sign
from sistemashn.core.licensing.license import LICENSE_PREFIX
from sistemashn.core.licensing.service import LicenseService
from sistemashn.core.setup.service import SetupService

VERTICAL = "repuestos"
APP_VERSION = "0.1.0"
KEY_ID = "dev-1"
FINGERPRINT = "f" * 64


def _public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


@pytest.fixture
def keypair():
    priv = Ed25519PrivateKey.generate()
    return priv, {KEY_ID: _public_bytes(priv)}


@pytest.fixture
def license_service(session_factory, keypair, clock) -> LicenseService:
    _, public_keys = keypair
    return LicenseService(
        session_factory, public_keys, fingerprint_fn=lambda: FINGERPRINT, clock=clock
    )


@pytest.fixture
def setup_service(session_factory, clock, license_service, tmp_path) -> SetupService:
    return SetupService(
        session_factory,
        clock,
        license_service,
        tmp_path / "data",
        VERTICAL,
        APP_VERSION,
    )


def build_license_text(
    priv,
    *,
    installation_id: str,
    vertical: str = VERTICAL,
    fingerprint: str = FINGERPRINT,
    business_name: str = "Repuestos Ejemplo",
) -> str:
    payload = {
        "license_id": "lic-1",
        "vertical": vertical,
        "business_name": business_name,
        "installation_id": installation_id,
        "fingerprint": fingerprint,
        "edition": "perpetua",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "format": 1,
        "key_id": KEY_ID,
    }
    return sign(priv, LICENSE_PREFIX, payload)
