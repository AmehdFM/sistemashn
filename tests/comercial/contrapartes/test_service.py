"""Pruebas de `PartyService` (plan T3.1)."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from sistemashn.comercial.contrapartes.errors import PossibleDuplicate
from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.core.errors import NotFound, PermissionDenied


def _proveedor(**overrides) -> PartyInput:
    data = {
        "kind": PartyKind.NEGOCIO,
        "name": "Repuestos El Motor",
        "rtn": "08011999123456",
        "is_supplier": True,
    }
    data.update(overrides)
    return PartyInput(**data)


def test_rtn_invalido_rechazado() -> None:
    with pytest.raises(PydanticValidationError):
        _proveedor(rtn="123")


def test_crear_contraparte(party_service, admin_actor) -> None:
    party_id = party_service.create(admin_actor, _proveedor())
    vista = party_service.get(admin_actor, party_id)
    assert vista.name == "Repuestos El Motor"
    assert vista.is_supplier is True
    assert vista.is_customer is False
    assert vista.active is True


def test_nombre_coincidente_sugiere_pero_no_fusiona(party_service, admin_actor) -> None:
    party_service.create(admin_actor, _proveedor())
    with pytest.raises(PossibleDuplicate) as exc_info:
        party_service.create(admin_actor, _proveedor(rtn=None, name="repuestos el motor"))
    candidatos = exc_info.value.candidates
    assert len(candidatos) == 1
    assert candidatos[0].name == "Repuestos El Motor"


def test_rtn_igual_sugiere_duplicado(party_service, admin_actor) -> None:
    party_service.create(admin_actor, _proveedor())
    with pytest.raises(PossibleDuplicate):
        party_service.create(admin_actor, _proveedor(name="Otro nombre distinto"))


def test_allow_duplicate_crea_de_todas_formas(party_service, admin_actor) -> None:
    primero = party_service.create(admin_actor, _proveedor())
    segundo = party_service.create(admin_actor, _proveedor(), allow_duplicate=True)
    assert primero != segundo


def test_proveedor_que_luego_es_cliente(party_service, admin_actor) -> None:
    party_id = party_service.create(admin_actor, _proveedor())
    party_service.set_roles(admin_actor, party_id, supplier=True, customer=True)
    vista = party_service.get(admin_actor, party_id)
    assert vista.is_supplier is True
    assert vista.is_customer is True


def test_set_active(party_service, admin_actor) -> None:
    party_id = party_service.create(admin_actor, _proveedor())
    party_service.set_active(admin_actor, party_id, False)
    vista = party_service.get(admin_actor, party_id)
    assert vista.active is False


def test_get_inexistente(party_service, admin_actor) -> None:
    with pytest.raises(NotFound):
        party_service.get(admin_actor, 9999)


def test_busqueda_por_nombre_sin_acentos(party_service, admin_actor) -> None:
    party_service.create(admin_actor, _proveedor(name="Almacén José Pérez", rtn=None))
    resultado = party_service.search(admin_actor, "almacen jose perez")
    assert resultado.total == 1
    assert resultado.items[0].name == "Almacén José Pérez"


def test_busqueda_por_rtn(party_service, admin_actor) -> None:
    party_service.create(admin_actor, _proveedor())
    resultado = party_service.search(admin_actor, "08011999123456")
    assert resultado.total == 1


def test_busqueda_filtra_por_rol(party_service, admin_actor) -> None:
    party_service.create(admin_actor, _proveedor(name="Solo proveedor", rtn=None))
    party_service.create(
        admin_actor,
        _proveedor(name="Solo cliente", rtn=None, is_supplier=False, is_customer=True),
    )
    solo_proveedores = party_service.search(admin_actor, "", role="supplier")
    assert {p.name for p in solo_proveedores.items} == {"Solo proveedor"}


def test_vendedor_sin_permiso_no_puede_gestionar(party_service, vendedor_actor) -> None:
    with pytest.raises(PermissionDenied):
        party_service.create(vendedor_actor, _proveedor())


def test_bodega_puede_gestionar(party_service, bodega_actor) -> None:
    party_id = party_service.create(bodega_actor, _proveedor())
    assert party_service.get(bodega_actor, party_id).id == party_id
