"""Pruebas de `CatalogService` (plan T2.1)."""

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from sistemashn.comercial.catalogo.schemas import CategoryInput, UnitInput
from sistemashn.comercial.inventario.models import Stock
from sistemashn.core.errors import PermissionDenied, ValidationError

from ..conftest import make_product_input


def test_crear_unidad_y_categoria(catalog_service, admin_actor) -> None:
    unit_id = catalog_service.create_unit(
        admin_actor, UnitInput(code="lt", name="Litro", allows_fraction=True)
    )
    category_id = catalog_service.create_category(admin_actor, CategoryInput(name="Aceites"))
    unidades = catalog_service.list_units(admin_actor)
    categorias = catalog_service.list_categories(admin_actor)
    assert unidades[0].id == unit_id
    assert unidades[0].code == "LT"
    assert categorias[0].id == category_id


def test_crear_producto_no_kit_crea_fila_de_stock_en_cero(
    catalog_service, admin_actor, session_factory, unidad_id, categoria_id
) -> None:
    product_id = catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, categoria_id)
    )
    with session_factory() as session:
        stock = session.get(Stock, product_id)
        assert stock is not None
        assert stock.on_hand == Decimal("0")
        assert stock.avg_cost == Decimal("0")


def test_crear_kit_no_crea_fila_de_stock(
    catalog_service, admin_actor, session_factory, unidad_id
) -> None:
    product_id = catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, is_kit=True, code="KIT-1")
    )
    with session_factory() as session:
        assert session.get(Stock, product_id) is None


def test_codigo_duplicado_rechazado(catalog_service, admin_actor, unidad_id) -> None:
    catalog_service.create_product(admin_actor, make_product_input(unidad_id))
    with pytest.raises(ValidationError):
        catalog_service.create_product(
            admin_actor, make_product_input(unidad_id, code="abc-123", barcode="999")
        )


def test_barcode_duplicado_rechazado(catalog_service, admin_actor, unidad_id) -> None:
    catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, barcode="7501234567890")
    )
    with pytest.raises(ValidationError):
        catalog_service.create_product(
            admin_actor,
            make_product_input(unidad_id, code="OTRO-1", barcode="7501234567890"),
        )


def test_codigo_vacio_rechazado(unidad_id) -> None:
    with pytest.raises(PydanticValidationError):
        make_product_input(unidad_id, code="   ")


def test_tasa_invalida_rechazada(unidad_id) -> None:
    with pytest.raises(PydanticValidationError):
        make_product_input(unidad_id, tax_rate="0.10")


def test_precio_negativo_rechazado(unidad_id) -> None:
    with pytest.raises(PydanticValidationError):
        make_product_input(unidad_id, sale_price="-1")


def test_vendedor_sin_permiso_no_crea_producto(catalog_service, vendedor_actor, unidad_id) -> None:
    with pytest.raises(PermissionDenied):
        catalog_service.create_product(vendedor_actor, make_product_input(unidad_id))


def test_vendedor_puede_ver_catalogo(
    catalog_service, admin_actor, vendedor_actor, unidad_id
) -> None:
    product_id = catalog_service.create_product(admin_actor, make_product_input(unidad_id))
    vista = catalog_service.get_product(vendedor_actor, product_id)
    assert vista.id == product_id


def test_costo_oculto_sin_permiso_com_costos_ver(
    catalog_service, admin_actor, vendedor_actor, unidad_id
) -> None:
    product_id = catalog_service.create_product(admin_actor, make_product_input(unidad_id))
    vista_vendedor = catalog_service.get_product(vendedor_actor, product_id)
    vista_admin = catalog_service.get_product(admin_actor, product_id)
    assert vista_vendedor.avg_cost is None
    assert vista_admin.avg_cost == Decimal("0.0000")


def test_editar_producto_audita_antes_despues_de_precio(
    catalog_service, admin_actor, session_factory, unidad_id
) -> None:
    product_id = catalog_service.create_product(admin_actor, make_product_input(unidad_id))
    catalog_service.update_product(
        admin_actor, product_id, make_product_input(unidad_id, sale_price="200.00")
    )
    vista = catalog_service.get_product(admin_actor, product_id)
    assert vista.sale_price == Decimal("200.00")


def test_inactivar_producto(catalog_service, admin_actor, unidad_id) -> None:
    product_id = catalog_service.create_product(admin_actor, make_product_input(unidad_id))
    catalog_service.set_active(admin_actor, product_id, False)
    vista = catalog_service.get_product(admin_actor, product_id)
    assert vista.active is False


def test_buscar_por_nombre_con_y_sin_acentos(catalog_service, admin_actor, unidad_id) -> None:
    catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, code="FRE-1", name="Pastillas Freón")
    )
    resultado = catalog_service.search(admin_actor, "freon")
    assert resultado.total == 1
    resultado_acento = catalog_service.search(admin_actor, "freón")
    assert resultado_acento.total == 1


def test_buscar_por_codigo(catalog_service, admin_actor, unidad_id) -> None:
    product_id = catalog_service.create_product(admin_actor, make_product_input(unidad_id))
    resultado = catalog_service.search(admin_actor, "abc-123")
    assert resultado.items[0].id == product_id


def test_buscar_prioriza_coincidencia_exacta_de_codigo(
    catalog_service, admin_actor, unidad_id
) -> None:
    catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, code="ABC", name="Producto ABC generico")
    )
    catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, code="ZZZ-ABC", name="Otro producto")
    )
    resultado = catalog_service.search(admin_actor, "ABC")
    assert resultado.items[0].code == "ABC"


def test_busqueda_paginada(catalog_service, admin_actor, unidad_id) -> None:
    for i in range(5):
        catalog_service.create_product(
            admin_actor, make_product_input(unidad_id, code=f"COD-{i}", name=f"Producto {i}")
        )
    pagina1 = catalog_service.search(admin_actor, "producto", page=1, page_size=2)
    pagina2 = catalog_service.search(admin_actor, "producto", page=2, page_size=2)
    assert pagina1.total == 5
    assert len(pagina1.items) == 2
    assert len(pagina2.items) == 2
    assert {p.id for p in pagina1.items}.isdisjoint({p.id for p in pagina2.items})


def test_find_by_code_or_barcode(catalog_service, admin_actor, unidad_id) -> None:
    product_id = catalog_service.create_product(
        admin_actor, make_product_input(unidad_id, barcode="123456")
    )
    por_codigo = catalog_service.find_by_code_or_barcode(admin_actor, "abc-123")
    por_barcode = catalog_service.find_by_code_or_barcode(admin_actor, "123456")
    inexistente = catalog_service.find_by_code_or_barcode(admin_actor, "no-existe")
    assert por_codigo.id == product_id
    assert por_barcode.id == product_id
    assert inexistente is None


class _FakeSearchProvider:
    """Proveedor de búsqueda falso que agrega un id fijo a los resultados."""

    def __init__(self, extra_id: int) -> None:
        self.extra_id = extra_id

    def search(self, session, text, limit):
        return [self.extra_id]


def test_proveedor_de_busqueda_externo_agrega_resultados(
    admin_actor, unidad_id, session_factory, authorizer, clock
) -> None:
    from sistemashn.comercial.catalogo.service import CatalogService

    servicio_base = CatalogService(session_factory, authorizer, clock=clock)
    producto_no_coincidente_id = servicio_base.create_product(
        admin_actor, make_product_input(unidad_id, code="XYZ-999", name="No relacionado")
    )

    servicio_con_proveedor = CatalogService(
        session_factory,
        authorizer,
        clock=clock,
        search_providers=[_FakeSearchProvider(producto_no_coincidente_id)],
    )
    resultado = servicio_con_proveedor.search(admin_actor, "texto-que-no-coincide-con-nada")
    assert any(p.id == producto_no_coincidente_id for p in resultado.items)


def test_categoria_o_unidad_inexistente_rechazada(catalog_service, admin_actor, unidad_id) -> None:
    with pytest.raises(ValidationError):
        catalog_service.create_product(admin_actor, make_product_input(999))
    with pytest.raises(ValidationError):
        catalog_service.create_product(admin_actor, make_product_input(unidad_id, category_id=999))
