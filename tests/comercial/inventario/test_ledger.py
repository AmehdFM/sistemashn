"""Pruebas del libro de inventario (T2.2): exactitud del promedio ponderado y atomicidad."""

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from sistemashn.comercial.catalogo.schemas import ProductInput
from sistemashn.comercial.inventario.errors import InsufficientStock, InvalidQuantity
from sistemashn.comercial.inventario.kinds import MovementKind
from sistemashn.comercial.inventario.models import Stock, StockMovement
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, ValidationError


def test_receive_promedio_ponderado_simple(
    session_factory, inventory_ledger, admin_actor, producto_id, clock
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        return inventory_ledger.receive(
            session, admin_actor, producto_id, Decimal("10"), Decimal("120")
        )

    nuevo_avg = run_in_transaction(session_factory, _op)
    assert nuevo_avg == Decimal("110.0000")

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("20")
        assert stock.avg_cost == Decimal("110.0000")


def test_receive_promedio_exacto_tres_compras_fraccionarias(
    session_factory, inventory_ledger, admin_actor, producto_fraccion_id
):
    def _op(session):
        inventory_ledger.receive(
            session, admin_actor, producto_fraccion_id, Decimal("10"), Decimal("100")
        )
        inventory_ledger.receive(
            session, admin_actor, producto_fraccion_id, Decimal("5"), Decimal("130")
        )
        return inventory_ledger.receive(
            session, admin_actor, producto_fraccion_id, Decimal("2.5"), Decimal("90")
        )

    nuevo_avg = run_in_transaction(session_factory, _op)

    # Cálculo manual con Decimal, igual regla que el ledger.
    total = Decimal("10") * Decimal("100") + Decimal("5") * Decimal("130")
    avg_1 = (total / Decimal("15")).quantize(Decimal("0.0001"))
    total_2 = Decimal("15") * avg_1 + Decimal("2.5") * Decimal("90")
    avg_2 = (total_2 / Decimal("17.5")).quantize(Decimal("0.0001"))

    assert nuevo_avg == avg_2

    with session_factory() as session:
        stock = session.get(Stock, producto_fraccion_id)
        assert stock.on_hand == Decimal("17.500")
        assert stock.avg_cost == avg_2


def test_receive_tras_stock_cero_toma_costo_nuevo(
    session_factory, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("5"), Decimal("50"))
        inventory_ledger.issue(session, admin_actor, producto_id, Decimal("5"))
        return inventory_ledger.receive(
            session, admin_actor, producto_id, Decimal("3"), Decimal("200")
        )

    nuevo_avg = run_in_transaction(session_factory, _op)
    assert nuevo_avg == Decimal("200.0000")


def test_issue_devuelve_costo_vigente(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        return inventory_ledger.issue(session, admin_actor, producto_id, Decimal("4"))

    costo = run_in_transaction(session_factory, _op)
    assert costo == Decimal("100.0000")

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("6")


def test_issue_insuficiente(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("5"), Decimal("100"))
        inventory_ledger.issue(session, admin_actor, producto_id, Decimal("10"))

    with pytest.raises(InsufficientStock) as exc_info:
        run_in_transaction(session_factory, _op)

    assert exc_info.value.product_id == producto_id
    assert exc_info.value.available == Decimal("5")
    assert exc_info.value.requested == Decimal("10")

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("0")


def test_reserve_y_issue_reserved(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.reserve(session, admin_actor, producto_id, Decimal("4"))
        return inventory_ledger.issue_reserved(session, admin_actor, producto_id, Decimal("4"))

    costo = run_in_transaction(session_factory, _op)
    assert costo == Decimal("100.0000")

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("6")
        assert stock.reserved == Decimal("0")


def test_reserve_reduce_disponible_no_fisico(
    session_factory, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.reserve(session, admin_actor, producto_id, Decimal("4"))

    run_in_transaction(session_factory, _op)

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("10")
        assert stock.reserved == Decimal("4")


def test_release_mas_de_lo_reservado_falla(
    session_factory, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.reserve(session, admin_actor, producto_id, Decimal("2"))
        inventory_ledger.release(session, admin_actor, producto_id, Decimal("5"))

    with pytest.raises(InsufficientStock):
        run_in_transaction(session_factory, _op)

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        # La transacción entera revierte: ni la reserva original queda.
        assert stock.reserved == Decimal("0")


def test_fraccion_en_unidad_entera_falla(
    session_factory, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("1.5"), Decimal("100"))

    with pytest.raises(InvalidQuantity):
        run_in_transaction(session_factory, _op)


def test_cantidad_no_positiva_falla(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("0"), Decimal("100"))

    with pytest.raises(InvalidQuantity):
        run_in_transaction(session_factory, _op)


def test_producto_inexistente_falla(session_factory, inventory_ledger, admin_actor):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, 999, Decimal("1"), Decimal("100"))

    with pytest.raises(NotFound):
        run_in_transaction(session_factory, _op)


def test_kit_no_tiene_existencias_propias(
    session_factory, inventory_ledger, admin_actor, catalog_service, unidad_id, categoria_id
):
    kit_id = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="KIT-1",
            name="Kit de frenos",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("500"),
            is_kit=True,
        ),
    )

    def _op(session):
        inventory_ledger.receive(session, admin_actor, kit_id, Decimal("1"), Decimal("100"))

    with pytest.raises(ValidationError):
        run_in_transaction(session_factory, _op)


def test_move_to_unsellable_no_afecta_on_hand(
    session_factory, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.move_to_unsellable(
            session, admin_actor, producto_id, Decimal("2"), Decimal("100")
        )

    run_in_transaction(session_factory, _op)

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("10")
        assert stock.unsellable == Decimal("2")


def test_unsellable_to_sellable_recalcula_promedio(
    session_factory, inventory_ledger, admin_actor, producto_id
):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.move_to_unsellable(
            session, admin_actor, producto_id, Decimal("2"), Decimal("100")
        )
        return inventory_ledger.unsellable_to_sellable(
            session, admin_actor, producto_id, Decimal("2"), Decimal("50")
        )

    nuevo_avg = run_in_transaction(session_factory, _op)
    # (10*100 + 2*50) / 12
    esperado = (
        (Decimal("10") * Decimal("100") + Decimal("2") * Decimal("50")) / Decimal("12")
    ).quantize(Decimal("0.0001"))
    assert nuevo_avg == esperado

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("12")
        assert stock.unsellable == Decimal("0")


def test_unsellable_out(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("10"), Decimal("100"))
        inventory_ledger.move_to_unsellable(
            session, admin_actor, producto_id, Decimal("2"), Decimal("100")
        )
        inventory_ledger.unsellable_out(
            session, admin_actor, producto_id, Decimal("2"), kind=MovementKind.SUPPLIER_RETURN_OUT
        )

    run_in_transaction(session_factory, _op)

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.unsellable == Decimal("0")


def test_adjust_in_out(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.adjust_in(
            session, admin_actor, producto_id, Decimal("5"), Decimal("80"), "conteo físico"
        )
        inventory_ledger.adjust_out(session, admin_actor, producto_id, Decimal("2"), "merma")

    run_in_transaction(session_factory, _op)

    with session_factory() as session:
        stock = session.get(Stock, producto_id)
        assert stock.on_hand == Decimal("3")
        movimientos = session.query(StockMovement).filter_by(product_id=producto_id).all()
        kinds = {m.kind for m in movimientos}
        assert kinds == {MovementKind.ADJUSTMENT_IN.value, MovementKind.ADJUSTMENT_OUT.value}


def test_movimiento_es_inmutable(session_factory, inventory_ledger, admin_actor, producto_id):
    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_id, Decimal("5"), Decimal("100"))

    run_in_transaction(session_factory, _op)

    with session_factory() as session:
        movimiento = session.query(StockMovement).filter_by(product_id=producto_id).one()
        movimiento_id = movimiento.id

    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE com_stock_movement SET reason = 'x' WHERE id = :id"),
            {"id": movimiento_id},
        )
        session.commit()

    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(
            text("DELETE FROM com_stock_movement WHERE id = :id"), {"id": movimiento_id}
        )
        session.commit()


def test_check_on_hand_no_negativo_a_nivel_sql(session_factory, producto_id):
    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE com_stock SET on_hand = -1 WHERE product_id = :id"), {"id": producto_id}
        )
        session.commit()


def test_dos_issue_en_una_transaccion_revierten_ambos_si_falla_el_segundo(
    session_factory, inventory_ledger, admin_actor, catalog_service, unidad_id, categoria_id
):
    producto_a = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="A-1",
            name="A",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("10"),
        ),
    )
    producto_b = catalog_service.create_product(
        admin_actor,
        ProductInput(
            code="B-1",
            name="B",
            unit_id=unidad_id,
            category_id=categoria_id,
            tax_rate=Decimal("0.15"),
            sale_price=Decimal("10"),
        ),
    )

    def _op(session):
        inventory_ledger.receive(session, admin_actor, producto_a, Decimal("10"), Decimal("50"))
        inventory_ledger.issue(session, admin_actor, producto_a, Decimal("5"))
        # producto_b no tiene existencias: la segunda salida falla y toda la transacción revierte.
        inventory_ledger.issue(session, admin_actor, producto_b, Decimal("1"))

    with pytest.raises(InsufficientStock):
        run_in_transaction(session_factory, _op)

    with session_factory() as session:
        stock_a = session.get(Stock, producto_a)
        assert stock_a.on_hand == Decimal("0")
        movimientos_a = session.query(StockMovement).filter_by(product_id=producto_a).all()
        assert movimientos_a == []
