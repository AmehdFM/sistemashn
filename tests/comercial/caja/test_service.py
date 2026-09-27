"""Pruebas de `CashService` (plan T4.3)."""

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from sistemashn.comercial.caja.errors import CashSessionAlreadyOpen, NoCashSessionOpen
from sistemashn.comercial.caja.models import CashMovement
from sistemashn.core.errors import PermissionDenied, ValidationError


def test_abrir_caja_crea_sesion_abierta(cash_service, admin_actor, now):
    vista = cash_service.open(admin_actor, Decimal("500.00"))

    assert vista.status == "abierta"
    assert vista.opening_amount == Decimal("500.00")
    assert vista.opened_by == admin_actor.user_id
    assert vista.closed_at is None
    assert cash_service.current(admin_actor).id == vista.id


def test_abrir_con_sesion_ya_abierta_falla_y_no_crea_una_segunda(cash_service, admin_actor):
    cash_service.open(admin_actor, Decimal("500.00"))

    with pytest.raises(CashSessionAlreadyOpen):
        cash_service.open(admin_actor, Decimal("100.00"))

    pagina = cash_service.list_sessions(admin_actor)
    assert pagina.total == 1


def test_abrir_con_monto_negativo_falla(cash_service, admin_actor):
    with pytest.raises(ValidationError):
        cash_service.open(admin_actor, Decimal("-1.00"))


def test_cerrar_sin_sesion_abierta_falla(cash_service, admin_actor):
    with pytest.raises(NoCashSessionOpen):
        cash_service.close(admin_actor, Decimal("0.00"))


def test_cerrar_sin_movimientos_calcula_esperado_igual_a_apertura(cash_service, admin_actor):
    cash_service.open(admin_actor, Decimal("100.00"))

    vista = cash_service.close(admin_actor, Decimal("100.00"))

    assert vista.status == "cerrada"
    assert vista.expected_cash == Decimal("100.00")
    assert vista.counted_cash == Decimal("100.00")
    assert vista.difference == Decimal("0.00")
    assert vista.closed_by == admin_actor.user_id
    assert cash_service.current(admin_actor) is None


def test_cerrar_con_movimientos_calcula_esperado_correcto(
    cash_service, admin_actor, session_factory
):
    sesion = cash_service.open(admin_actor, Decimal("100.00"))
    cash_service.manual_entry(admin_actor, Decimal("50.00"), "depósito de refuerzo")
    cash_service.manual_exit(admin_actor, Decimal("20.00"), "compra de bolsas")

    with session_factory() as session:
        cash_service.register_entry(
            session, admin_actor, sesion.id, Decimal("30.00"), "venta", ref_type="sale", ref_id="1"
        )
        cash_service.register_entry(
            session,
            admin_actor,
            sesion.id,
            Decimal("15.00"),
            "abono",
            ref_type="account",
            ref_id="2",
        )
        session.commit()

    # 100 + 50 - 20 + 30 + 15 = 175
    vista = cash_service.close(admin_actor, Decimal("175.00"))
    assert vista.expected_cash == Decimal("175.00")
    assert vista.difference == Decimal("0.00")


def test_cerrar_con_diferencia_positiva(cash_service, admin_actor):
    cash_service.open(admin_actor, Decimal("100.00"))
    vista = cash_service.close(admin_actor, Decimal("110.00"))
    assert vista.difference == Decimal("10.00")


def test_cerrar_con_diferencia_negativa(cash_service, admin_actor):
    cash_service.open(admin_actor, Decimal("100.00"))
    vista = cash_service.close(admin_actor, Decimal("90.00"))
    assert vista.difference == Decimal("-10.00")


def test_entrada_manual_requiere_motivo_minimo(cash_service, admin_actor):
    cash_service.open(admin_actor, Decimal("100.00"))

    with pytest.raises(ValidationError):
        cash_service.manual_entry(admin_actor, Decimal("10.00"), "")

    with pytest.raises(ValidationError):
        cash_service.manual_entry(admin_actor, Decimal("10.00"), "abc")


def test_salida_manual_requiere_motivo_minimo(cash_service, admin_actor):
    cash_service.open(admin_actor, Decimal("100.00"))

    with pytest.raises(ValidationError):
        cash_service.manual_exit(admin_actor, Decimal("10.00"), "no")


def test_entrada_manual_sin_sesion_abierta_falla(cash_service, admin_actor):
    with pytest.raises(NoCashSessionOpen):
        cash_service.manual_entry(admin_actor, Decimal("10.00"), "motivo válido")


def test_salida_manual_sin_sesion_abierta_falla(cash_service, admin_actor):
    with pytest.raises(NoCashSessionOpen):
        cash_service.manual_exit(admin_actor, Decimal("10.00"), "motivo válido")


def test_register_entry_interno_inserta_movimiento(cash_service, admin_actor, session_factory):
    sesion = cash_service.open(admin_actor, Decimal("100.00"))

    with session_factory() as session:
        cash_service.register_entry(
            session, admin_actor, sesion.id, Decimal("25.00"), "venta", ref_type="sale", ref_id="1"
        )
        session.commit()

    pagina = cash_service.movements(admin_actor, sesion.id)
    assert pagina.total == 1
    assert pagina.items[0].amount == Decimal("25.00")
    assert pagina.items[0].kind == "venta"
    assert pagina.items[0].ref_type == "sale"


def test_register_entry_sin_sesion_abierta_falla(cash_service, admin_actor, session_factory):
    sesion = cash_service.open(admin_actor, Decimal("100.00"))
    cash_service.close(admin_actor, Decimal("100.00"))

    with session_factory() as session, pytest.raises(NoCashSessionOpen):
        cash_service.register_entry(session, admin_actor, sesion.id, Decimal("10.00"), "venta")


def test_register_entry_monto_no_positivo_falla(cash_service, admin_actor, session_factory):
    sesion = cash_service.open(admin_actor, Decimal("100.00"))

    with session_factory() as session, pytest.raises(ValidationError):
        cash_service.register_entry(session, admin_actor, sesion.id, Decimal("0.00"), "venta")


def test_movimiento_es_append_only(cash_service, admin_actor, session_factory):
    sesion = cash_service.open(admin_actor, Decimal("100.00"))
    with session_factory() as session:
        cash_service.register_entry(session, admin_actor, sesion.id, Decimal("25.00"), "venta")
        session.commit()

    with session_factory() as session:
        movimiento_id = session.query(CashMovement).filter_by(cash_session_id=sesion.id).one().id

    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE com_cash_movement SET amount = 999 WHERE id = :id"), {"id": movimiento_id}
        )
        session.commit()

    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(text("DELETE FROM com_cash_movement WHERE id = :id"), {"id": movimiento_id})
        session.commit()


def test_movements_paginado(cash_service, admin_actor, session_factory):
    sesion = cash_service.open(admin_actor, Decimal("100.00"))
    with session_factory() as session:
        for i in range(3):
            cash_service.register_entry(
                session, admin_actor, sesion.id, Decimal("10.00"), "venta", ref_id=str(i)
            )
        session.commit()

    pagina = cash_service.movements(admin_actor, sesion.id, page=1, page_size=2)
    assert pagina.total == 3
    assert len(pagina.items) == 2

    pagina2 = cash_service.movements(admin_actor, sesion.id, page=2, page_size=2)
    assert len(pagina2.items) == 1


def test_list_sessions_ordena_mas_reciente_primero(cash_service, admin_actor):
    primera = cash_service.open(admin_actor, Decimal("50.00"))
    cash_service.close(admin_actor, Decimal("50.00"))
    segunda = cash_service.open(admin_actor, Decimal("60.00"))

    pagina = cash_service.list_sessions(admin_actor)
    assert pagina.total == 2
    assert pagina.items[0].id == segunda.id
    assert pagina.items[1].id == primera.id


def test_bodega_no_puede_abrir_ni_operar_caja(cash_service, bodega_actor):
    with pytest.raises(PermissionDenied):
        cash_service.open(bodega_actor, Decimal("100.00"))

    with pytest.raises(PermissionDenied):
        cash_service.manual_entry(bodega_actor, Decimal("10.00"), "motivo válido")


def test_vendedor_puede_operar_pero_no_cerrar(cash_service, admin_actor, vendedor_actor):
    cash_service.open(admin_actor, Decimal("100.00"))
    cash_service.manual_entry(vendedor_actor, Decimal("10.00"), "depósito de refuerzo")

    with pytest.raises(PermissionDenied):
        cash_service.close(vendedor_actor, Decimal("110.00"))
