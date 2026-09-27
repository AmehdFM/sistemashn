"""Pruebas de normalización de número de parte y búsqueda extensible (T2.4)."""

from tests.repuestos.conftest import make_product_input

from sistemashn.repuestos.partes.search import normalize_part_number


def test_normalize_part_number_quita_separadores():
    assert normalize_part_number(" ph-16.b/2 ") == "PH16B2"


def test_normalize_part_number_ya_normalizado():
    assert normalize_part_number("PH16") == "PH16"


def test_busqueda_por_numero_de_parte_y_equivalente(
    catalog_service, part_service, admin_actor, unidad_id, categoria_id
):
    principal = catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, categoria_id, code="A-1", name="Bomba A")
    )
    equivalente = catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, categoria_id, code="B-1", name="Bomba B")
    )
    part_service.set_part_info(admin_actor, principal, "PH-16", None, "original")
    part_service.set_part_info(admin_actor, equivalente, "16PH", None, "generico")
    part_service.link_equivalent(admin_actor, principal, equivalente)

    pagina = catalog_service.search(admin_actor, "ph16")
    ids = {p.id for p in pagina.items}
    assert ids == {principal, equivalente}


def test_busqueda_texto_corto_no_usa_proveedor(
    catalog_service, part_service, admin_actor, unidad_id, categoria_id
):
    producto = catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, categoria_id, code="A-1", name="Bomba A")
    )
    part_service.set_part_info(admin_actor, producto, "PH", None, "original")

    pagina = catalog_service.search(admin_actor, "ph")
    ids = {p.id for p in pagina.items}
    assert producto not in ids
