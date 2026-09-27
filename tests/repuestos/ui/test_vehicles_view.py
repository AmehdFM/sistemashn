"""Pruebas de la pantalla de vehículos de Repuestos (T2.6b)."""

from sistemashn.repuestos.ui.vehicles_view import build_vehicles_view


def test_build_sin_datos(ctx_admin) -> None:
    control = build_vehicles_view(ctx_admin)
    assert control is not None


def test_build_con_datos(ctx_admin) -> None:
    vehicles = ctx_admin.service("vehicles")
    make_id = vehicles.create_make(ctx_admin.actor, "Toyota")
    vehicles.create_model(ctx_admin.actor, make_id, "Corolla")

    control = build_vehicles_view(ctx_admin)
    assert control is not None
