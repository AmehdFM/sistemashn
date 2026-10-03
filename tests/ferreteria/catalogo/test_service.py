"""Contrato de presentaciones: cantidades exactas y SKU aislados."""

from decimal import Decimal

import pytest

from sistemashn.comercial.catalogo.schemas import ProductInput, UnitInput
from sistemashn.comercial.catalogo.service import CatalogService
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.errors import PermissionDenied, ValidationError
from sistemashn.core.identity.models import User
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE
from sistemashn.ferreteria.catalogo.search import FerreteriaSearchProvider
from sistemashn.ferreteria.catalogo.service import FerreteriaCatalogService
from sistemashn.ferreteria.module import FERRETERIA_MODULE


@pytest.fixture
def services(session_factory, now, clock):
    registry = ModuleRegistry()
    registry.register(CORE_MODULE)
    registry.register(COMERCIAL_MODULE)
    registry.register(FERRETERIA_MODULE)
    authorizer = Authorizer(registry, clock=clock)
    with session_factory() as session:
        user = User(
            username="fer_admin",
            full_name="Ferretería Admin",
            password_hash="hash",
            is_admin=True,
            is_active=True,
            profile_code=None,
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        actor = Actor(user_id=user.id, username=user.username, is_admin=True, session_id="fer")
    catalog = CatalogService(session_factory, authorizer, clock=clock)
    fer_catalog = FerreteriaCatalogService(session_factory, authorizer, clock=clock)
    return actor, catalog, fer_catalog


def _product(actor, catalog, *, code, fraction):
    unit_id = catalog.create_unit(
        actor, UnitInput(code=code[:20], name=code, allows_fraction=fraction)
    )
    return catalog.create_product(
        actor,
        ProductInput(
            code=code,
            name=code,
            unit_id=unit_id,
            tax_rate=Decimal("0"),
            sale_price=Decimal("10"),
            min_stock=Decimal("0"),
        ),
    )


def test_caja_de_100_y_pieza_se_convierten_sin_cambiar_stock(services, session_factory):
    actor, catalog, fer = services
    product_id = _product(actor, catalog, code="TORNILLO-M8-30", fraction=False)
    box_id = fer.create_pack(
        actor,
        product_id,
        code="789-CAJA",
        label="Caja de 100",
        factor_base=Decimal("100"),
        permits_fraction=False,
        price=Decimal("80.00"),
    )
    conversion = fer.convert_to_base(actor, box_id, Decimal("2"))
    assert conversion.quantity_base == Decimal("200")
    assert conversion.price == Decimal("80.00")
    assert fer.resolve_barcode(actor, "789-CAJA").id == box_id
    with pytest.raises(ValidationError, match="enteras"):
        fer.convert_to_base(actor, box_id, Decimal("0.250"))
    # Convertir solo describe la línea: los movimientos pertenecen al libro comercial.
    from sistemashn.comercial.inventario.models import Stock

    with session_factory() as session:
        assert session.get(Stock, product_id).on_hand == Decimal("0.000")


def test_corte_por_metro_y_precision_base_exacta(services):
    actor, catalog, fer = services
    product_id = _product(actor, catalog, code="CABLE-12AWG", fraction=True)
    roll_id = fer.create_pack(
        actor,
        product_id,
        code="ROLLO-50",
        label="Rollo de 50 m",
        factor_base="50",
        permits_fraction=True,
        price=None,
    )
    assert fer.convert_to_base(actor, roll_id, "0.025").quantity_base == Decimal("1.250")
    with pytest.raises(ValidationError, match="precisión"):
        fer.convert_to_base(actor, roll_id, "0.0001")

    small_id = fer.create_pack(
        actor,
        product_id,
        code=None,
        label="Tramo fino",
        factor_base="0.0001",
        permits_fraction=True,
    )
    with pytest.raises(ValidationError, match="cantidad base"):
        fer.convert_to_base(actor, small_id, "1")


def test_unidad_indivisible_y_codigos_colisionantes(services):
    actor, catalog, fer = services
    product_id = _product(actor, catalog, code="TORNILLO", fraction=False)
    with pytest.raises(ValidationError, match="indivisible"):
        fer.create_pack(
            actor,
            product_id,
            code=None,
            label="Media pieza",
            factor_base="0.5",
            permits_fraction=False,
        )
    with pytest.raises(ValidationError, match="usado por un producto"):
        fer.create_pack(
            actor,
            product_id,
            code="TORNILLO",
            label="Caja",
            factor_base="10",
            permits_fraction=False,
        )


def test_ficha_y_presentacion_requieren_permiso(services, session_factory, now):
    actor, catalog, fer = services
    product_id = _product(actor, catalog, code="PVC-MEDIO", fraction=False)
    fer.set_item(actor, product_id, brand="Marca X", family="Plomería", specs="PVC 1/2")
    assert fer.get_item(actor, product_id).brand == "Marca X"

    with session_factory() as session:
        user = User(
            username="solo_lectura",
            full_name="Solo lectura",
            password_hash="hash",
            is_admin=False,
            is_active=True,
            profile_code="vendedor",
            permissions_version=1,
            failed_attempts=0,
            locked_until=None,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        viewer = Actor(user_id=user.id, username=user.username, is_admin=False, session_id="view")
    assert fer.get_item(viewer, product_id).family == "Plomería"
    with pytest.raises(PermissionDenied):
        fer.set_item(viewer, product_id, brand="Otra")


def test_factor_y_precio_no_se_redondean_en_silencio(services):
    actor, catalog, fer = services
    product_id = _product(actor, catalog, code="CABLE", fraction=True)
    with pytest.raises(ValidationError, match="precio"):
        fer.create_pack(
            actor,
            product_id,
            code=None,
            label="Metro",
            factor_base="1",
            permits_fraction=True,
            price="10.001",
        )
    with pytest.raises(ValidationError, match="float"):
        fer.create_pack(
            actor,
            product_id,
            code=None,
            label="Metro",
            factor_base=0.1,
            permits_fraction=True,
        )


def test_no_cambiar_unidad_base_con_presentacion_y_no_duplicar_barra(services):
    actor, catalog, fer = services
    product_id = _product(actor, catalog, code="MANGUERA", fraction=True)
    other_unit = catalog.create_unit(
        actor, UnitInput(code="PIEZA", name="Pieza", allows_fraction=False)
    )
    fer.create_pack(
        actor,
        product_id,
        code="ROLLO-50",
        label="Rollo",
        factor_base="50",
        permits_fraction=False,
    )
    with pytest.raises(ValidationError, match="unidad base"):
        catalog.update_product(
            actor,
            product_id,
            ProductInput(
                code="MANGUERA",
                name="Manguera",
                unit_id=other_unit,
                tax_rate="0",
                sale_price="10",
            ),
        )
    with pytest.raises(ValidationError, match="presentación"):
        catalog.create_product(
            actor,
            ProductInput(
                code="MANGUERA-OTRA",
                barcode="ROLLO-50",
                name="Otra manguera",
                unit_id=other_unit,
                tax_rate="0",
                sale_price="10",
            ),
        )


def test_migracion_ferreteria_crea_tablas_e_indices(tmp_path):
    from sqlalchemy import create_engine, inspect

    from sistemashn.core.db.migrate import current_revision, upgrade

    path = tmp_path / "migracion-ferreteria.db"
    upgrade(path)
    assert current_revision(path) == "0009"
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    try:
        inspector = inspect(engine)
        assert {"fer_item", "fer_pack"}.issubset(inspector.get_table_names())
        assert "ix_fer_pack_product_id" in {
            row["name"] for row in inspector.get_indexes("fer_pack")
        }
        assert "presentation_snapshot" in {
            row["name"] for row in inspector.get_columns("com_purchase_line")
        }
    finally:
        engine.dispose()


def test_busqueda_de_barra_y_especificacion_devuelve_sku_dueño(services, session_factory):
    actor, catalog, fer = services
    cable_id = _product(actor, catalog, code="CABLE-AWG12", fraction=True)
    otro_id = _product(actor, catalog, code="CABLE-AWG14", fraction=True)
    fer.set_item(actor, cable_id, brand="Eléctrica", family="Cable", specs="Calibre 12")
    fer.set_item(actor, otro_id, brand="Eléctrica", family="Cable", specs="Calibre 14")
    fer.create_pack(
        actor,
        cable_id,
        code="ROLLO-AWG12",
        label="Rollo 50 m",
        factor_base="50",
        permits_fraction=False,
    )
    provider = FerreteriaSearchProvider()
    with session_factory() as session:
        assert provider.search(session, "ROLLO-AWG12", 10) == [cable_id]
        assert provider.search(session, "calibre 14", 10) == [otro_id]
