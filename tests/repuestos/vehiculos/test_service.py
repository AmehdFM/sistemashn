"""Pruebas de `VehicleService`: marcas y modelos (T2.4)."""

import pytest

from sistemashn.core.errors import NotFound, PermissionDenied, ValidationError


def test_create_make_y_list_makes(vehicle_service, admin_actor):
    vehicle_service.create_make(admin_actor, "Toyota")
    marcas = vehicle_service.list_makes(admin_actor)
    assert [m.name for m in marcas] == ["Toyota"]


def test_create_make_duplicado_sin_distinguir_mayusculas(vehicle_service, admin_actor):
    vehicle_service.create_make(admin_actor, "Toyota")
    with pytest.raises(ValidationError):
        vehicle_service.create_make(admin_actor, "TOYOTA")


def test_create_model_y_list_models(vehicle_service, admin_actor):
    make_id = vehicle_service.create_make(admin_actor, "Toyota")
    vehicle_service.create_model(admin_actor, make_id, "Corolla")
    modelos = vehicle_service.list_models(admin_actor, make_id)
    assert [m.name for m in modelos] == ["Corolla"]


def test_create_model_duplicado_misma_marca(vehicle_service, admin_actor):
    make_id = vehicle_service.create_make(admin_actor, "Toyota")
    vehicle_service.create_model(admin_actor, make_id, "Corolla")
    with pytest.raises(ValidationError):
        vehicle_service.create_model(admin_actor, make_id, "corolla")


def test_create_model_marca_inexistente(vehicle_service, admin_actor):
    with pytest.raises(NotFound):
        vehicle_service.create_model(admin_actor, 999, "Corolla")


def test_vendedor_no_gestiona_vehiculos(vehicle_service, admin_actor, vendedor_actor):
    make_id = vehicle_service.create_make(admin_actor, "Toyota")
    with pytest.raises(PermissionDenied):
        vehicle_service.create_model(vendedor_actor, make_id, "Corolla")
