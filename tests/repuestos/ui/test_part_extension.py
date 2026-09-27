"""Pruebas de la extensión de formulario de producto de Repuestos (T2.6b)."""

from sistemashn.comercial.catalogo.schemas import ProductInput
from sistemashn.repuestos.ui.part_extension import PartFormExtension


def _crear_producto(ctx_admin) -> int:
    catalog = ctx_admin.service("catalog")
    from sistemashn.comercial.catalogo.schemas import UnitInput

    unidad_id = catalog.create_unit(ctx_admin.actor, UnitInput(code="UND", name="Unidad"))
    return catalog.create_product(
        ctx_admin.actor,
        ProductInput(
            code="PH-16", name="Filtro", unit_id=unidad_id, tax_rate="0.15", sale_price="10"
        ),
    )


def test_is_visible_con_permiso(ctx_admin) -> None:
    extension = PartFormExtension()
    assert extension.is_visible(ctx_admin) is True
    assert extension.title == "Datos de repuesto"


def test_build_sin_datos_de_parte(ctx_admin) -> None:
    producto_id = _crear_producto(ctx_admin)
    extension = PartFormExtension()
    control = extension.build(ctx_admin, producto_id)
    assert control is not None


def test_build_con_datos_equivalencias_y_compatibilidad(ctx_admin) -> None:
    producto_id = _crear_producto(ctx_admin)
    parts = ctx_admin.service("parts")
    vehicles = ctx_admin.service("vehicles")
    catalog = ctx_admin.service("catalog")

    parts.set_part_info(ctx_admin.actor, producto_id, "PH-16", "Purolator", "original")

    otro_producto_id = catalog.create_product(
        ctx_admin.actor,
        ProductInput(
            code="PH-16B",
            name="Filtro equivalente",
            unit_id=catalog.get_product(ctx_admin.actor, producto_id).unit_id,
            tax_rate="0.15",
            sale_price="10",
        ),
    )
    parts.set_part_info(ctx_admin.actor, otro_producto_id, "PH-16B", "Bosch", "generico")
    parts.link_equivalent(ctx_admin.actor, producto_id, otro_producto_id)

    make_id = vehicles.create_make(ctx_admin.actor, "Toyota")
    model_id = vehicles.create_model(ctx_admin.actor, make_id, "Corolla")
    parts.add_compatibility(ctx_admin.actor, producto_id, model_id, 2010, 2015)

    extension = PartFormExtension()
    control = extension.build(ctx_admin, producto_id)
    assert control is not None
