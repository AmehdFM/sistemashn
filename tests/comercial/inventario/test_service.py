"""Pruebas del `InventoryService` (T2.2): ajustes, consulta, stock bajo, reconciliación."""

from decimal import Decimal

import pytest

from sistemashn.comercial.catalogo.schemas import ProductInput
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import PermissionDenied, ValidationError


def test_adjust_entrada_actualiza_costo_y_audita(
    session_factory, inventory_service, admin_actor, producto_id
):
    inventory_service.adjust(
        admin_actor, producto_id, Decimal("5"), "conteo físico", unit_cost=Decimal("40")
    )
    stock = inventory_service.stock(admin_actor, producto_id)
    assert stock.on_hand == Decimal("5")
    assert stock.avg_cost == Decimal("40.0000")

    with session_factory() as session:
        from sistemashn.core.audit.models import AuditEvent

        evento = session.query(AuditEvent).filter_by(action="com.inventario.ajuste").one()
        assert evento.entity_id == str(producto_id)


def test_adjust_salida(session_factory, inventory_service, admin_actor, producto_id):
    inventory_service.adjust(
        admin_actor, producto_id, Decimal("10"), "carga inicial", unit_cost=Decimal("20")
    )
    inventory_service.adjust(admin_actor, producto_id, Decimal("-3"), "merma detectada")
    stock = inventory_service.stock(admin_actor, producto_id)
    assert stock.on_hand == Decimal("7")


def test_adjust_motivo_muy_corto_falla(inventory_service, admin_actor, producto_id):
    with pytest.raises(ValidationError):
        inventory_service.adjust(admin_actor, producto_id, Decimal("5"), "abc")


def test_adjust_cero_falla(inventory_service, admin_actor, producto_id):
    with pytest.raises(ValidationError):
        inventory_service.adjust(admin_actor, producto_id, Decimal("0"), "motivo válido")


def test_adjust_vendedor_sin_permiso(inventory_service, vendedor_actor, producto_id):
    with pytest.raises(PermissionDenied):
        inventory_service.adjust(vendedor_actor, producto_id, Decimal("5"), "motivo válido")


def test_stock_oculta_costo_sin_permiso(inventory_service, vendedor_actor, producto_id):
    stock = inventory_service.stock(vendedor_actor, producto_id)
    assert stock.avg_cost is None
    assert stock.on_hand == Decimal("0")


def test_stock_muestra_costo_con_permiso(inventory_service, admin_actor, producto_id):
    inventory_service.adjust(
        admin_actor, producto_id, Decimal("5"), "carga inicial", unit_cost=Decimal("30")
    )
    stock = inventory_service.stock(admin_actor, producto_id)
    assert stock.avg_cost == Decimal("30.0000")


def test_movements_pagina_y_ordena_recientes_primero(inventory_service, admin_actor, producto_id):
    inventory_service.adjust(
        admin_actor, producto_id, Decimal("5"), "carga inicial", unit_cost=Decimal("10")
    )
    inventory_service.adjust(admin_actor, producto_id, Decimal("2"), "otra carga")
    pagina = inventory_service.movements(admin_actor, producto_id, page=1, page_size=10)
    assert pagina.total == 2
    assert len(pagina.items) == 2


def test_low_stock_lista_productos_bajo_minimo(
    session_factory, inventory_service, catalog_service, admin_actor, unidad_id, categoria_id
):
    bajo_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="BAJO-1",
            name="Producto bajo mínimo",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("10"),
            min_stock=Decimal("5"),
        ),
    )
    alto_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="ALTO-1",
            name="Producto sobre mínimo",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("10"),
            min_stock=Decimal("5"),
        ),
    )
    inventory_service.adjust(
        admin_actor, bajo_id, Decimal("2"), "carga inicial", unit_cost=Decimal("1")
    )
    inventory_service.adjust(
        admin_actor, alto_id, Decimal("10"), "carga inicial", unit_cost=Decimal("1")
    )

    pagina = inventory_service.low_stock(admin_actor, page=1, page_size=10)
    ids = {item.product_id for item in pagina.items}
    assert bajo_id in ids
    assert alto_id not in ids


def test_reconcile_verdadero_tras_secuencia_mixta(
    session_factory, inventory_service, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.reserve(session, admin_actor, producto_id, Decimal("3"))
        inventory_ledger.issue_reserved(session, admin_actor, producto_id, Decimal("2"))
        inventory_ledger.move_to_unsellable(
            session, admin_actor, producto_id, Decimal("1"), Decimal("100")
        )

    run_in_transaction(session_factory, _op)

    with session_factory() as session:
        assert inventory_service.reconcile(session, producto_id) is True
