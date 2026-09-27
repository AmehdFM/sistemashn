"""Pruebas de LicenseService: solicitud, instalación y consulta (T1.4)."""

from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from sistemashn.core.licensing.codec import sign
from sistemashn.core.licensing.license import (
    LICENSE_PREFIX,
    LicenseError,
    parse_request_code,
)
from sistemashn.core.licensing.models import InstalledLicense
from sistemashn.core.licensing.service import LicenseService

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


def _license_text(priv, *, license_id="lic-1", fingerprint=FINGERPRINT) -> str:
    payload = {
        "license_id": license_id,
        "vertical": VERTICAL,
        "business_name": "Repuestos Ejemplo",
        "installation_id": INSTALLATION_ID,
        "fingerprint": fingerprint,
        "edition": "perpetua",
        "issued_at": "2026-01-01T00:00:00+00:00",
        "format": 1,
        "key_id": KEY_ID,
    }
    return sign(priv, LICENSE_PREFIX, payload)


def _service(
    session_factory, public_keys, *, fingerprint=FINGERPRINT, clock=None
) -> LicenseService:
    kwargs = {"fingerprint_fn": lambda: fingerprint}
    if clock is not None:
        kwargs["clock"] = clock
    return LicenseService(session_factory, public_keys, **kwargs)


def test_request_code_incluye_huella_actual(session_factory, keypair) -> None:
    _, public_keys = keypair
    service = _service(session_factory, public_keys)

    texto = service.request_code(INSTALLATION_ID, VERTICAL, "0.1.0")
    payload = parse_request_code(texto)
    assert payload["fingerprint"] == FINGERPRINT
    assert payload["installation_id"] == INSTALLATION_ID
    assert payload["vertical"] == VERTICAL


def test_install_guarda_y_current_la_recupera(session_factory, keypair, clock) -> None:
    priv, public_keys = keypair
    service = _service(session_factory, public_keys, clock=clock)
    texto = _license_text(priv)

    instalada = service.install(texto, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert instalada.license_id == "lic-1"

    actual = service.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert actual is not None
    assert actual.license_id == "lic-1"
    assert actual.raw_text == texto


def test_current_sin_licencia_instalada_retorna_none(session_factory, keypair) -> None:
    _, public_keys = keypair
    service = _service(session_factory, public_keys)
    assert service.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID) is None


def test_install_rechaza_licencia_invalida_y_no_guarda_nada(session_factory, keypair) -> None:
    priv, public_keys = keypair
    service = _service(session_factory, public_keys, fingerprint="0" * 64)
    texto = _license_text(priv)  # firmada para FINGERPRINT, no para "0"*64

    with pytest.raises(LicenseError) as excinfo:
        service.install(texto, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert excinfo.value.reason == "maquina"
    assert service.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID) is None


def test_current_con_huella_cambiada_lanza_error_maquina(session_factory, keypair, clock) -> None:
    priv, public_keys = keypair
    service = _service(session_factory, public_keys, clock=clock)
    texto = _license_text(priv)
    service.install(texto, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)

    # Simula un cambio de hardware: la huella actual ya no coincide con la instalada.
    service_otra_maquina = _service(session_factory, public_keys, fingerprint="0" * 64, clock=clock)
    with pytest.raises(LicenseError) as excinfo:
        service_otra_maquina.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert excinfo.value.reason == "maquina"


def test_install_reemplaza_dejando_historial(session_factory, keypair, clock) -> None:
    priv, public_keys = keypair
    service = _service(session_factory, public_keys, clock=clock)

    texto1 = _license_text(priv, license_id="lic-1")
    texto2 = _license_text(priv, license_id="lic-2")

    service.install(texto1, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    service.install(texto2, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)

    with session_factory() as session:
        filas = session.execute(select(InstalledLicense)).scalars().all()
    assert len(filas) == 2
    assert {f.license_id for f in filas} == {"lic-1", "lic-2"}

    actual = service.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert actual is not None
    assert actual.license_id == "lic-2"


def test_reloj_muy_adelantado_no_afecta_validez(session_factory, keypair) -> None:
    priv, public_keys = keypair
    futuro = lambda: datetime(2099, 1, 1, tzinfo=UTC)  # noqa: E731
    service = _service(session_factory, public_keys, clock=futuro)
    texto = _license_text(priv)

    service.install(texto, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    actual = service.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert actual is not None and actual.license_id == "lic-1"


def test_reloj_muy_atrasado_no_afecta_validez(session_factory, keypair) -> None:
    priv, public_keys = keypair
    pasado = lambda: datetime(1990, 1, 1, tzinfo=UTC)  # noqa: E731
    service = _service(session_factory, public_keys, clock=pasado)
    texto = _license_text(priv)

    service.install(texto, expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    actual = service.current(expected_vertical=VERTICAL, installation_id=INSTALLATION_ID)
    assert actual is not None and actual.license_id == "lic-1"
