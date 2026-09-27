"""Pruebas de `PartService`: datos de parte, equivalencias y compatibilidad (T2.4)."""

import pytest
from tests.repuestos.conftest import make_product_input

from sistemashn.core.errors import NotFound, PermissionDenied, ValidationError


def _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, **overrides):
    data = make_product_input(unidad_id, categoria_id, **overrides)
    return catalog_service.create_product(admin_actor, data)


def test_set_part_info_crea_y_actualiza(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)

    part_service.set_part_info(admin_actor, product_id, "ph-16", "Fabricante A", "original")
    vista = part_service.get_part(admin_actor, product_id)
    assert vista.part_number == "ph-16"
    assert vista.manufacturer == "Fabricante A"
    assert vista.origin == "original"

    part_service.set_part_info(admin_actor, product_id, "PH-16B", "Fabricante B", "generico")
    vista = part_service.get_part(admin_actor, product_id)
    assert vista.part_number == "PH-16B"
    assert vista.manufacturer == "Fabricante B"
    assert vista.origin == "generico"


def test_set_part_info_origen_invalido(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    with pytest.raises(ValidationError):
        part_service.set_part_info(admin_actor, product_id, "PH-16", None, "invalido")


def test_set_part_info_producto_inexistente(part_service, admin_actor):
    with pytest.raises(NotFound):
        part_service.set_part_info(admin_actor, 999, "PH-16", None, "original")


def test_get_part_inexistente(part_service, catalog_service, admin_actor, unidad_id, categoria_id):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    with pytest.raises(NotFound):
        part_service.get_part(admin_actor, product_id)


def test_vendedor_no_gestiona_partes(
    part_service, catalog_service, admin_actor, vendedor_actor, unidad_id, categoria_id
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    with pytest.raises(PermissionDenied):
        part_service.set_part_info(vendedor_actor, product_id, "PH-16", None, "original")


def test_link_equivalent_crea_grupo_y_es_idempotente(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    a = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="A-1")
    b = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="B-1")
    part_service.set_part_info(admin_actor, a, "PH-16", None, "original")
    part_service.set_part_info(admin_actor, b, "16-PH", None, "generico")

    part_service.link_equivalent(admin_actor, a, b)
    equivalentes_a = part_service.equivalents(admin_actor, a)
    assert [e.id for e in equivalentes_a] == [b]

    # idempotente: repetir el vínculo no debe fallar ni duplicar
    part_service.link_equivalent(admin_actor, a, b)
    equivalentes_a = part_service.equivalents(admin_actor, a)
    assert [e.id for e in equivalentes_a] == [b]


def test_link_equivalent_une_ungrouped_a_grupo(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    a = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="A-1")
    b = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="B-1")
    c = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="C-1")
    for pid, numero in ((a, "P1"), (b, "P2"), (c, "P3")):
        part_service.set_part_info(admin_actor, pid, numero, None, "original")

    part_service.link_equivalent(admin_actor, a, b)
    part_service.link_equivalent(admin_actor, a, c)

    equivalentes_b = {e.id for e in part_service.equivalents(admin_actor, b)}
    assert equivalentes_b == {a, c}


def test_link_equivalent_fusiona_grupos_de_dos(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    a = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="A-1")
    b = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="B-1")
    c = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="C-1")
    d = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="D-1")
    for pid, numero in ((a, "P1"), (b, "P2"), (c, "P3"), (d, "P4")):
        part_service.set_part_info(admin_actor, pid, numero, None, "original")

    part_service.link_equivalent(admin_actor, a, b)
    part_service.link_equivalent(admin_actor, c, d)
    part_service.link_equivalent(admin_actor, a, c)

    equivalentes_a = {e.id for e in part_service.equivalents(admin_actor, a)}
    assert equivalentes_a == {b, c, d}
    equivalentes_d = {e.id for e in part_service.equivalents(admin_actor, d)}
    assert equivalentes_d == {a, b, c}


def test_unlink_deja_grupo_de_uno_vacio(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    a = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="A-1")
    b = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="B-1")
    part_service.set_part_info(admin_actor, a, "P1", None, "original")
    part_service.set_part_info(admin_actor, b, "P2", None, "original")
    part_service.link_equivalent(admin_actor, a, b)

    part_service.unlink(admin_actor, a)

    assert part_service.equivalents(admin_actor, a) == []
    assert part_service.equivalents(admin_actor, b) == []
    vista_b = part_service.get_part(admin_actor, b)
    assert vista_b.equivalence_group_id is None


def test_equivalents_excluye_producto_inactivo(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    a = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="A-1")
    b = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="B-1")
    part_service.set_part_info(admin_actor, a, "P1", None, "original")
    part_service.set_part_info(admin_actor, b, "P2", None, "original")
    part_service.link_equivalent(admin_actor, a, b)

    catalog_service.set_active(admin_actor, b, False)

    assert part_service.equivalents(admin_actor, a) == []


def test_add_compatibility_rechaza_year_from_mayor(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id, model_id
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    with pytest.raises(ValidationError):
        part_service.add_compatibility(admin_actor, product_id, model_id, 2010, 2005)


@pytest.mark.parametrize(("year_from", "year_to"), [(1949, 1949), (2101, 2101)])
def test_add_compatibility_rechaza_anios_fuera_de_rango(
    part_service,
    catalog_service,
    admin_actor,
    unidad_id,
    categoria_id,
    model_id,
    year_from,
    year_to,
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    with pytest.raises(ValidationError):
        part_service.add_compatibility(admin_actor, product_id, model_id, year_from, year_to)


def test_add_compatibility_extremos_validos(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id, model_id
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    compat_id = part_service.add_compatibility(admin_actor, product_id, model_id, 1950, 2100)
    compatibilidades = part_service.compatibilities(admin_actor, product_id)
    assert [c.id for c in compatibilidades] == [compat_id]


def test_remove_compatibility(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id, model_id
):
    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    compat_id = part_service.add_compatibility(admin_actor, product_id, model_id, 2000, 2010)
    part_service.remove_compatibility(admin_actor, compat_id)
    assert part_service.compatibilities(admin_actor, product_id) == []


def test_compatible_products_por_anio_y_excluye_inactivos(
    part_service, catalog_service, admin_actor, unidad_id, categoria_id, model_id
):
    dentro = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="D-1")
    fuera = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="F-1")
    inactivo = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id, code="I-1")
    part_service.add_compatibility(admin_actor, dentro, model_id, 2005, 2012)
    part_service.add_compatibility(admin_actor, fuera, model_id, 2015, 2020)
    part_service.add_compatibility(admin_actor, inactivo, model_id, 2005, 2012)
    catalog_service.set_active(admin_actor, inactivo, False)

    pagina = part_service.compatible_products(admin_actor, model_id, 2010)
    ids = {p.id for p in pagina.items}
    assert ids == {dentro}


def test_producto_compartido_entre_marcas(
    part_service, catalog_service, vehicle_service, admin_actor, unidad_id, categoria_id, make_id
):
    modelo_a = vehicle_service.create_model(admin_actor, make_id, "Corolla")
    otra_marca = vehicle_service.create_make(admin_actor, "Honda")
    modelo_b = vehicle_service.create_model(admin_actor, otra_marca, "Civic")

    product_id = _crear_producto(catalog_service, admin_actor, unidad_id, categoria_id)
    part_service.add_compatibility(admin_actor, product_id, modelo_a, 2000, 2010)
    part_service.add_compatibility(admin_actor, product_id, modelo_b, 2000, 2010)

    compatibilidades = part_service.compatibilities(admin_actor, product_id)
    assert {c.model_id for c in compatibilidades} == {modelo_a, modelo_b}
