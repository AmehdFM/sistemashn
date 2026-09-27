"""Pruebas de `FiscalService` (plan T4.5): emisión de factura fiscal (CAI), deshabilitada por
defecto y nunca fuera de rango o vigencia."""

from datetime import date, timedelta

import pytest
from tests.comercial.fiscal.conftest import set_business_fiscal

from sistemashn.comercial.fiscal.errors import (
    AlreadyInvoiced,
    AuthorizationExhausted,
    AuthorizationExpired,
    FiscalDisabled,
    NoActiveAuthorization,
)
from sistemashn.comercial.fiscal.schemas import FiscalAuthorizationInput
from sistemashn.core.errors import PermissionDenied


def _autorizacion(
    *,
    cai="A1B2C3-A1B2C3-A1B2C3-A1B2C3-A1B2C3",
    range_start="001-001-01-00000001",
    range_end="001-001-01-00000100",
    valid_until: date | None = None,
) -> FiscalAuthorizationInput:
    return FiscalAuthorizationInput(
        cai=cai,
        range_start=range_start,
        range_end=range_end,
        valid_until=valid_until or date(2030, 1, 1),
    )


def test_emitir_con_autorizacion_valida_consume_correlativo(
    fiscal_service, admin_actor, session_factory, now
):
    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    auth_id = fiscal_service.register_authorization(admin_actor, _autorizacion())

    factura = fiscal_service.issue(admin_actor, sale_id=1, snapshot={"total": "150.00"})

    assert factura.fiscal_number == "001-001-01-00000001"
    assert factura.sale_id == 1
    assert factura.authorization_id == auth_id

    autorizaciones = fiscal_service.list_authorizations(admin_actor)
    assert autorizaciones[0].next_correlative == 2
    assert autorizaciones[0].status == "activa"


def test_fiscal_deshabilitado_rechaza_sin_importar_autorizacion(
    fiscal_service, admin_actor, session_factory, now
):
    set_business_fiscal(session_factory, now, fiscal_enabled=False)
    fiscal_service.register_authorization(admin_actor, _autorizacion())

    with pytest.raises(FiscalDisabled):
        fiscal_service.issue(admin_actor, sale_id=1, snapshot={})


def test_sin_autorizacion_registrada(fiscal_service, admin_actor, session_factory, now):
    set_business_fiscal(session_factory, now, fiscal_enabled=True)

    with pytest.raises(NoActiveAuthorization):
        fiscal_service.issue(admin_actor, sale_id=1, snapshot={})


def test_autorizacion_vencida_marca_vencida_y_rechaza(
    fiscal_service, admin_actor, session_factory, now
):
    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    ayer = now.date() - timedelta(days=1)
    fiscal_service.register_authorization(admin_actor, _autorizacion(valid_until=ayer))

    with pytest.raises(AuthorizationExpired):
        fiscal_service.issue(admin_actor, sale_id=1, snapshot={})

    autorizaciones = fiscal_service.list_authorizations(admin_actor)
    assert autorizaciones[0].status == "vencida"


def test_rango_agotado(fiscal_service, admin_actor, session_factory, now):
    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    fiscal_service.register_authorization(
        admin_actor,
        _autorizacion(range_start="001-001-01-00000001", range_end="001-001-01-00000002"),
    )

    primera = fiscal_service.issue(admin_actor, sale_id=1, snapshot={})
    assert primera.fiscal_number == "001-001-01-00000001"
    segunda = fiscal_service.issue(admin_actor, sale_id=2, snapshot={})
    assert segunda.fiscal_number == "001-001-01-00000002"

    with pytest.raises(AuthorizationExhausted):
        fiscal_service.issue(admin_actor, sale_id=3, snapshot={})

    autorizaciones = fiscal_service.list_authorizations(admin_actor)
    assert autorizaciones[0].status == "agotada"


def test_doble_emision_misma_venta_rechazada_sin_consumir_correlativo(
    fiscal_service, admin_actor, session_factory, now
):
    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    fiscal_service.register_authorization(admin_actor, _autorizacion())
    fiscal_service.issue(admin_actor, sale_id=1, snapshot={})

    with pytest.raises(AlreadyInvoiced):
        fiscal_service.issue(admin_actor, sale_id=1, snapshot={})

    autorizaciones = fiscal_service.list_authorizations(admin_actor)
    assert autorizaciones[0].next_correlative == 2


def test_is_available_refleja_los_cuatro_escenarios(
    fiscal_service, admin_actor, session_factory, now
):
    # 1. Deshabilitado.
    set_business_fiscal(session_factory, now, fiscal_enabled=False)
    assert fiscal_service.is_available(admin_actor) is False

    # 2. Habilitado, sin autorización.
    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    assert fiscal_service.is_available(admin_actor) is False

    # 3. Habilitado, con autorización vencida.
    ayer = now.date() - timedelta(days=1)
    fiscal_service.register_authorization(admin_actor, _autorizacion(valid_until=ayer))
    assert fiscal_service.is_available(admin_actor) is False

    # 4. Habilitado, con autorización vigente.
    fiscal_service.register_authorization(
        admin_actor, _autorizacion(cai="B" * 37, valid_until=date(2030, 1, 1))
    )
    assert fiscal_service.is_available(admin_actor) is True


def test_permisos_registrar_y_emitir_requieren_fiscal_gestionar(
    fiscal_service, vendedor_actor, admin_actor, session_factory, now
):
    set_business_fiscal(session_factory, now, fiscal_enabled=True)
    fiscal_service.register_authorization(admin_actor, _autorizacion())

    with pytest.raises(PermissionDenied):
        fiscal_service.register_authorization(vendedor_actor, _autorizacion(cai="C" * 37))

    with pytest.raises(PermissionDenied):
        fiscal_service.issue(vendedor_actor, sale_id=1, snapshot={})
