"""Pruebas de kits (T2.3): composición, disponibilidad, expansión y atomicidad en venta."""

from decimal import Decimal

import pytest

from sistemashn.comercial.catalogo.kits import KitService, availability, explode
from sistemashn.comercial.inventario.errors import InsufficientStock
from sistemashn.comercial.inventario.models import Stock
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, PermissionDenied, ValidationError

from ..conftest import make_product_input


@pytest.fixture
def kit_service(session_factory, authorizer, clock) -> KitService:
    return KitService(session_factory, authorizer, clock=clock)


@pytest.fixture
def kit_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(
            unidad_id, categoria_id, code="KIT-1", name="Kit de frenos", is_kit=True
        ),
    )


@pytest.fixture
def componente_a_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="PAD-A", name="Pastilla A"),
    )


@pytest.fixture
def componente_b_id(catalog_service, admin_actor, unidad_id, categoria_id) -> int:
    return catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="PAD-B", name="Pastilla B"),
    )


def _recibir(session_factory, inventory_ledger, admin_actor, product_id, qty, cost):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, product_id, qty, cost)

    run_in_transaction(session_factory, _op)


# -- set_components -----------------------------------------------------------


def test_set_components_requiere_permiso(kit_service, vendedor_actor, kit_id, componente_a_id):
    with pytest.raises(PermissionDenied):
        kit_service.set_components(vendedor_actor, kit_id, [(componente_a_id, Decimal("1"))])


def test_set_components_kit_debe_existir(kit_service, admin_actor, componente_a_id):
    with pytest.raises(NotFound):
        kit_service.set_components(admin_actor, 9999, [(componente_a_id, Decimal("1"))])


def test_set_components_producto_no_kit_rechazado(
    kit_service, admin_actor, componente_a_id, componente_b_id
):
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, componente_a_id, [(componente_b_id, Decimal("1"))])


def test_set_components_vacio_rechazado(kit_service, admin_actor, kit_id):
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, kit_id, [])


def test_set_components_componente_inexistente(kit_service, admin_actor, kit_id):
    with pytest.raises(NotFound):
        kit_service.set_components(admin_actor, kit_id, [(9999, Decimal("1"))])


def test_set_components_componente_inactivo_rechazado(
    kit_service, catalog_service, admin_actor, kit_id, componente_a_id
):
    catalog_service.set_active(admin_actor, componente_a_id, False)
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, kit_id, [(componente_a_id, Decimal("1"))])


def test_set_components_componente_kit_rechazado(
    kit_service, catalog_service, admin_actor, unidad_id, categoria_id, kit_id
):
    otro_kit_id = catalog_service.create_product(
        admin_actor,
        make_product_input(unidad_id, categoria_id, code="KIT-2", name="Otro kit", is_kit=True),
    )
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, kit_id, [(otro_kit_id, Decimal("1"))])


def test_set_components_autorreferencia_rechazada(kit_service, admin_actor, kit_id):
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, kit_id, [(kit_id, Decimal("1"))])


def test_set_components_cantidad_cero_rechazada(kit_service, admin_actor, kit_id, componente_a_id):
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, kit_id, [(componente_a_id, Decimal("0"))])


def test_set_components_componente_repetido_rechazado(
    kit_service, admin_actor, kit_id, componente_a_id
):
    with pytest.raises(ValidationError):
        kit_service.set_components(
            admin_actor,
            kit_id,
            [(componente_a_id, Decimal("1")), (componente_a_id, Decimal("2"))],
        )


def test_set_components_fraccion_en_unidad_entera_rechazada(
    kit_service, admin_actor, kit_id, componente_a_id
):
    with pytest.raises(ValidationError):
        kit_service.set_components(admin_actor, kit_id, [(componente_a_id, Decimal("1.5"))])


def test_set_components_fraccion_en_unidad_fraccionaria_permitida(
    kit_service, admin_actor, kit_id, unidad_fraccion_id, categoria_id, catalog_service
):
    aceite_id = catalog_service.create_product(
        admin_actor,
        make_product_input(
            unidad_fraccion_id, categoria_id, code="ACEITE-KIT", name="Aceite de motor"
        ),
    )
    kit_service.set_components(admin_actor, kit_id, [(aceite_id, Decimal("0.5"))])
    vistas = kit_service.components(admin_actor, kit_id)
    assert len(vistas) == 1
    assert vistas[0].qty == Decimal("0.500")


def test_set_components_reemplaza_composicion_y_audita(
    kit_service, admin_actor, kit_id, componente_a_id, componente_b_id, session_factory
):
    kit_service.set_components(admin_actor, kit_id, [(componente_a_id, Decimal("2"))])
    kit_service.set_components(admin_actor, kit_id, [(componente_b_id, Decimal("3"))])

    vistas = kit_service.components(admin_actor, kit_id)
    assert len(vistas) == 1
    assert vistas[0].component_id == componente_b_id
    assert vistas[0].qty == Decimal("3.000")
    assert vistas[0].code == "PAD-B"

    from sistemashn.core.audit.models import AuditEvent

    with session_factory() as session:
        from sqlalchemy import select

        eventos = session.scalars(
            select(AuditEvent).where(AuditEvent.action == "com.kit.composicion")
        ).all()
        assert len(eventos) == 2


def test_components_requiere_permiso_ver(kit_service, kit_id):
    from sistemashn.core.authorization.actor import Actor

    anonimo = Actor(user_id=999, username="nadie", is_admin=False, session_id="s")
    with pytest.raises(PermissionDenied):
        kit_service.components(anonimo, kit_id)


# -- availability ---------------------------------------------------------


def test_availability_sin_componentes_es_cero(session_factory, kit_id):
    with session_factory() as session:
        assert availability(session, kit_id) == Decimal("0")


def test_availability_minimo_entre_componentes(
    kit_service,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
    session_factory,
    inventory_ledger,
):
    kit_service.set_components(
        admin_actor,
        kit_id,
        [(componente_a_id, Decimal("2")), (componente_b_id, Decimal("1"))],
    )
    _recibir(
        session_factory,
        inventory_ledger,
        admin_actor,
        componente_a_id,
        Decimal("10"),
        Decimal("50"),
    )
    _recibir(
        session_factory, inventory_ledger, admin_actor, componente_b_id, Decimal("3"), Decimal("20")
    )

    # A: 10/2 = 5 ; B: 3/1 = 3 -> mínimo 3
    with session_factory() as session:
        assert availability(session, kit_id) == Decimal("3")


def test_availability_componente_fraccionario(
    kit_service,
    admin_actor,
    kit_id,
    unidad_fraccion_id,
    categoria_id,
    catalog_service,
    session_factory,
    inventory_ledger,
):
    aceite_id = catalog_service.create_product(
        admin_actor,
        make_product_input(
            unidad_fraccion_id, categoria_id, code="ACEITE-DISP", name="Aceite de motor"
        ),
    )
    kit_service.set_components(admin_actor, kit_id, [(aceite_id, Decimal("0.5"))])
    _recibir(session_factory, inventory_ledger, admin_actor, aceite_id, Decimal("6"), Decimal("80"))

    # 6 / 0.5 = 12 kits enteros posibles
    with session_factory() as session:
        assert availability(session, kit_id) == Decimal("12")


def test_availability_trunca_a_entero(
    kit_service,
    admin_actor,
    kit_id,
    componente_a_id,
    session_factory,
    inventory_ledger,
):
    kit_service.set_components(admin_actor, kit_id, [(componente_a_id, Decimal("3"))])
    _recibir(
        session_factory,
        inventory_ledger,
        admin_actor,
        componente_a_id,
        Decimal("10"),
        Decimal("50"),
    )

    # 10 / 3 = 3.333... -> trunca a 3
    with session_factory() as session:
        assert availability(session, kit_id) == Decimal("3")


# -- explode ----------------------------------------------------------------


def test_explode_multiplica_cantidades_y_trae_costo(
    kit_service,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
    session_factory,
    inventory_ledger,
):
    kit_service.set_components(
        admin_actor,
        kit_id,
        [(componente_a_id, Decimal("2")), (componente_b_id, Decimal("1"))],
    )
    _recibir(
        session_factory,
        inventory_ledger,
        admin_actor,
        componente_a_id,
        Decimal("10"),
        Decimal("50"),
    )
    _recibir(
        session_factory,
        inventory_ledger,
        admin_actor,
        componente_b_id,
        Decimal("10"),
        Decimal("30"),
    )

    with session_factory() as session:
        lineas = explode(session, kit_id, Decimal("3"))

    por_componente = {linea.component_id: linea for linea in lineas}
    assert por_componente[componente_a_id].qty == Decimal("6.000")
    assert por_componente[componente_a_id].avg_cost == Decimal("50.0000")
    assert por_componente[componente_b_id].qty == Decimal("3.000")
    assert por_componente[componente_b_id].avg_cost == Decimal("30.0000")


def test_explode_cantidad_no_entera_rechazada(session_factory, kit_id):
    with session_factory() as session, pytest.raises(ValidationError):
        explode(session, kit_id, Decimal("1.5"))


def test_explode_cantidad_no_positiva_rechazada(session_factory, kit_id):
    with session_factory() as session, pytest.raises(ValidationError):
        explode(session, kit_id, Decimal("0"))


def test_explode_snapshot_no_se_altera_por_cambio_posterior(
    kit_service,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
    session_factory,
    inventory_ledger,
):
    kit_service.set_components(admin_actor, kit_id, [(componente_a_id, Decimal("2"))])
    _recibir(
        session_factory,
        inventory_ledger,
        admin_actor,
        componente_a_id,
        Decimal("10"),
        Decimal("50"),
    )

    with session_factory() as session:
        lineas_antes = explode(session, kit_id, Decimal("1"))

    kit_service.set_components(admin_actor, kit_id, [(componente_b_id, Decimal("5"))])

    assert len(lineas_antes) == 1
    assert lineas_antes[0].component_id == componente_a_id
    assert lineas_antes[0].qty == Decimal("2.000")


# -- Salida atómica: explode + issue por línea dentro de una transacción ----


def test_venta_de_kit_es_atomica_si_falta_un_componente(
    kit_service,
    admin_actor,
    kit_id,
    componente_a_id,
    componente_b_id,
    session_factory,
    inventory_ledger,
):
    kit_service.set_components(
        admin_actor,
        kit_id,
        [(componente_a_id, Decimal("1")), (componente_b_id, Decimal("1"))],
    )
    _recibir(
        session_factory,
        inventory_ledger,
        admin_actor,
        componente_a_id,
        Decimal("10"),
        Decimal("50"),
    )
    _recibir(
        session_factory, inventory_ledger, admin_actor, componente_b_id, Decimal("1"), Decimal("30")
    )

    def _vender(session):
        lineas = explode(session, kit_id, Decimal("2"))
        for linea in lineas:
            inventory_ledger.issue(session, admin_actor, linea.component_id, linea.qty)

    with pytest.raises(InsufficientStock):
        run_in_transaction(session_factory, _vender)

    with session_factory() as session:
        stock_a = session.get(Stock, componente_a_id)
        stock_b = session.get(Stock, componente_b_id)
        assert stock_a.on_hand == Decimal("10")
        assert stock_b.on_hand == Decimal("1")
