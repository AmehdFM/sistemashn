"""Pruebas de SettingsService: negocio, logo y valores tipados (T1.5)."""

import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from sistemashn.core.authorization.actor import SYSTEM_ACTOR
from sistemashn.core.errors import PermissionDenied, ValidationError
from sistemashn.core.settings.schemas import BusinessInput
from sistemashn.core.settings.service import MAX_LOGO_BYTES

from .conftest import actor_sin_permiso

DATOS = BusinessInput(
    name="Repuestos Ejemplo",
    legal_name="Repuestos Ejemplo S. de R.L.",
    rtn="08011999012345",
    address="Col. Centro",
    phone="9999-9999",
    email="ejemplo@correo.com",
)


def test_get_business_sin_datos_retorna_none(settings_service):
    assert settings_service.get_business() is None


def test_update_business_crea_y_actualiza(settings_service):
    settings_service.update_business(SYSTEM_ACTOR, DATOS)
    vista = settings_service.get_business()
    assert vista is not None
    assert vista.name == "Repuestos Ejemplo"
    assert vista.fiscal_enabled is False
    assert vista.prices_include_isv is True

    otros_datos = DATOS.model_copy(update={"name": "Repuestos Nuevo"})
    settings_service.update_business(SYSTEM_ACTOR, otros_datos)
    assert settings_service.get_business().name == "Repuestos Nuevo"


def test_update_business_sin_permiso_falla(settings_service):
    with pytest.raises(PermissionDenied):
        settings_service.update_business(actor_sin_permiso(), DATOS)
    assert settings_service.get_business() is None


def test_update_business_no_cambia_fiscal_enabled(settings_service, session_factory):
    settings_service.update_business(SYSTEM_ACTOR, DATOS)

    from sistemashn.core.settings.models import Business

    with session_factory() as session:
        negocio = session.get(Business, 1)
        negocio.fiscal_enabled = True
        session.commit()

    settings_service.update_business(SYSTEM_ACTOR, DATOS)
    assert settings_service.get_business().fiscal_enabled is True


def test_rtn_invalido_rechazado_por_el_esquema():
    with pytest.raises(PydanticValidationError):
        BusinessInput(name="x", legal_name="x", rtn="123", address="x", phone="x", email="x@x.com")


def test_set_logo_png_valido(settings_service, tmp_path):
    settings_service.update_business(SYSTEM_ACTOR, DATOS)
    origen = tmp_path / "logo.png"
    origen.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)

    settings_service.set_logo(SYSTEM_ACTOR, origen)

    vista = settings_service.get_business()
    assert vista.logo_path == "logo.png"
    assert (settings_service.data_dir / "logo.png").exists()


def test_set_logo_reemplaza_el_anterior(settings_service, tmp_path):
    settings_service.update_business(SYSTEM_ACTOR, DATOS)
    png = tmp_path / "a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)
    settings_service.set_logo(SYSTEM_ACTOR, png)

    jpg = tmp_path / "b.jpg"
    jpg.write_bytes(b"\xff\xd8\xff" + b"0" * 10)
    settings_service.set_logo(SYSTEM_ACTOR, jpg)

    assert settings_service.get_business().logo_path == "logo.jpg"
    assert not (settings_service.data_dir / "logo.png").exists()
    assert (settings_service.data_dir / "logo.jpg").exists()


def test_set_logo_texto_con_extension_png_falla(settings_service, tmp_path):
    settings_service.update_business(SYSTEM_ACTOR, DATOS)
    falso = tmp_path / "falso.png"
    falso.write_bytes(b"esto no es una imagen")

    with pytest.raises(ValidationError):
        settings_service.set_logo(SYSTEM_ACTOR, falso)


def test_set_logo_demasiado_grande_falla(settings_service, tmp_path):
    settings_service.update_business(SYSTEM_ACTOR, DATOS)
    grande = tmp_path / "grande.png"
    grande.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (MAX_LOGO_BYTES + 1))

    with pytest.raises(ValidationError):
        settings_service.set_logo(SYSTEM_ACTOR, grande)


class _Preferencias(BaseModel):
    tema: str = "grafito"
    filas_por_pagina: int = 25


def test_get_set_valor_tipado(settings_service):
    assert settings_service.get("preferencias", _Preferencias) is None

    settings_service.set(SYSTEM_ACTOR, "preferencias", _Preferencias(tema="vino"))
    leido = settings_service.get("preferencias", _Preferencias)
    assert leido == _Preferencias(tema="vino")


def test_set_valor_sin_permiso_falla(settings_service):
    with pytest.raises(PermissionDenied):
        settings_service.set(actor_sin_permiso(), "preferencias", _Preferencias())
