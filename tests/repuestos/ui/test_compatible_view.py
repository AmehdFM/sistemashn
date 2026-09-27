"""Pruebas de la pantalla de búsqueda por vehículo compatible (T2.6b)."""

from sistemashn.repuestos.ui.compatible_view import build_compatible_view


def test_build_sin_datos(ctx_admin) -> None:
    control = build_compatible_view(ctx_admin)
    assert control is not None


def test_build_con_datos(ctx_admin) -> None:
    vehicles = ctx_admin.service("vehicles")
    catalog = ctx_admin.service("catalog")
    parts = ctx_admin.service("parts")

    from sistemashn.comercial.catalogo.schemas import ProductInput, UnitInput

    unidad_id = catalog.create_unit(ctx_admin.actor, UnitInput(code="UND", name="Unidad"))

    producto_id = catalog.create_product(
        ctx_admin.actor,
        ProductInput(
            code="PH-16", name="Filtro", unit_id=unidad_id, tax_rate="0.15", sale_price="10"
        ),
    )
    make_id = vehicles.create_make(ctx_admin.actor, "Toyota")
    model_id = vehicles.create_model(ctx_admin.actor, make_id, "Corolla")
    parts.add_compatibility(ctx_admin.actor, producto_id, model_id, 2010, 2015)

    control = build_compatible_view(ctx_admin)
    assert control is not None
