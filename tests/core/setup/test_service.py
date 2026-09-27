"""Pruebas de SetupService: flujo de primer arranque (T1.5)."""

import pytest

from sistemashn.core.errors import ValidationError
from sistemashn.core.licensing.license import LicenseError
from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.setup.service import SetupService, SetupStep

from .conftest import build_license_text

DATOS_NEGOCIO = BusinessInput(
    name="Repuestos Ejemplo",
    legal_name="Repuestos Ejemplo S. de R.L.",
    rtn="08011999012345",
    address="Col. Centro",
    phone="9999-9999",
    email="ejemplo@correo.com",
)


def _avanzar_hasta_admin(setup_service, keypair) -> None:
    instalacion = setup_service.ensure_installation()
    priv, _ = keypair
    texto = build_license_text(priv, installation_id=instalacion.installation_id)
    setup_service.submit_license(texto)
    setup_service.submit_business(DATOS_NEGOCIO)


def test_ensure_installation_es_idempotente(setup_service):
    primera = setup_service.ensure_installation()
    segunda = setup_service.ensure_installation()
    assert primera.installation_id == segunda.installation_id
    assert primera.setup_step == SetupStep.LICENSE


def test_state_en_license_incluye_request_code(setup_service):
    setup_service.ensure_installation()
    estado = setup_service.state()
    assert estado.step == SetupStep.LICENSE
    assert estado.request_code is not None
    assert estado.request_code.startswith("SHNREQ1.")


def test_flujo_completo_hasta_done(setup_service, keypair):
    instalacion = setup_service.ensure_installation()
    priv, _ = keypair
    texto = build_license_text(priv, installation_id=instalacion.installation_id)

    setup_service.submit_license(texto)
    assert setup_service.state().step == SetupStep.BUSINESS

    setup_service.submit_business(DATOS_NEGOCIO)
    assert setup_service.state().step == SetupStep.ADMIN

    codigos = setup_service.create_admin("admin", "Admin Principal", "clave1234")
    assert len(codigos) == 8
    assert setup_service.state().step == SetupStep.RECOVERY

    setup_service.confirm_recovery_codes_saved()
    estado = setup_service.state()
    assert estado.step == SetupStep.DONE
    assert estado.request_code is None


def test_submit_license_invalida_propaga_license_error(setup_service, keypair):
    setup_service.ensure_installation()
    priv, _ = keypair
    # Firmada para otra instalación.
    texto = build_license_text(priv, installation_id="otra-instalacion")

    with pytest.raises(LicenseError):
        setup_service.submit_license(texto)
    assert setup_service.state().step == SetupStep.LICENSE


def test_pasos_fuera_de_orden_fallan(setup_service, keypair):
    setup_service.ensure_installation()
    with pytest.raises(ValidationError):
        setup_service.submit_business(DATOS_NEGOCIO)
    with pytest.raises(ValidationError):
        setup_service.create_admin("admin", "Admin", "clave1234")
    with pytest.raises(ValidationError):
        setup_service.confirm_recovery_codes_saved()


def test_repetir_submit_tras_done_falla(setup_service, keypair):
    _avanzar_hasta_admin(setup_service, keypair)
    setup_service.create_admin("admin", "Admin Principal", "clave1234")
    setup_service.confirm_recovery_codes_saved()

    with pytest.raises(ValidationError):
        setup_service.submit_license("SHN1.x.y")
    with pytest.raises(ValidationError):
        setup_service.submit_business(DATOS_NEGOCIO)
    with pytest.raises(ValidationError):
        setup_service.create_admin("otro", "Otro", "clave1234")
    with pytest.raises(ValidationError):
        setup_service.confirm_recovery_codes_saved()


def test_contrasena_debil_no_crea_admin_ni_avanza(setup_service, keypair, session_factory):
    _avanzar_hasta_admin(setup_service, keypair)

    with pytest.raises(ValidationError):
        setup_service.create_admin("admin", "Admin Principal", "corta")

    assert setup_service.state().step == SetupStep.ADMIN

    from sistemashn.core.identity.models import User

    with session_factory() as session:
        assert session.query(User).count() == 0


def test_interrupcion_entre_pasos_nueva_instancia_retoma(
    session_factory, clock, license_service, tmp_path, keypair
):
    data_dir = tmp_path / "data"
    servicio_1 = SetupService(
        session_factory, clock, license_service, data_dir, "repuestos", "0.1.0"
    )
    instalacion = servicio_1.ensure_installation()
    priv, _ = keypair
    texto = build_license_text(priv, installation_id=instalacion.installation_id)
    servicio_1.submit_license(texto)

    # Instancia nueva: mismo backing store, retoma en `business`.
    servicio_2 = SetupService(
        session_factory, clock, license_service, data_dir, "repuestos", "0.1.0"
    )
    assert servicio_2.state().step == SetupStep.BUSINESS
    servicio_2.submit_business(DATOS_NEGOCIO)
    assert servicio_2.state().step == SetupStep.ADMIN


def test_regenerar_codigos_solo_en_paso_recovery(setup_service, keypair):
    _avanzar_hasta_admin(setup_service, keypair)

    with pytest.raises(ValidationError):
        setup_service.regenerate_recovery_codes_during_setup()

    primeros = setup_service.create_admin("admin", "Admin Principal", "clave1234")
    nuevos = setup_service.regenerate_recovery_codes_during_setup()

    assert len(nuevos) == 8
    assert set(nuevos).isdisjoint(primeros)

    setup_service.confirm_recovery_codes_saved()
    with pytest.raises(ValidationError):
        setup_service.regenerate_recovery_codes_during_setup()


def test_logo_invalido_en_submit_business_falla(setup_service, keypair, tmp_path):
    instalacion = setup_service.ensure_installation()
    priv, _ = keypair
    texto = build_license_text(priv, installation_id=instalacion.installation_id)
    setup_service.submit_license(texto)

    falso = tmp_path / "falso.png"
    falso.write_bytes(b"esto no es una imagen")

    with pytest.raises(ValidationError):
        setup_service.submit_business(DATOS_NEGOCIO, falso)
    assert setup_service.state().step == SetupStep.BUSINESS
