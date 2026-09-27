"""Pruebas de `AccountService`: abonos, saldo, estados derivados y permisos (plan T3.3)."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from sistemashn.comercial.contrapartes.schemas import PartyInput, PartyKind
from sistemashn.comercial.credito.errors import OverpaymentError, RequestIdReused
from sistemashn.comercial.credito.models import Account, AccountPayment
from sistemashn.comercial.credito.schemas import AccountKind, AccountStatus
from sistemashn.comercial.pagos.methods import PaymentInput, PaymentMethod
from sistemashn.core.db.uow import run_in_transaction
from sistemashn.core.errors import NotFound, PermissionDenied, ValidationError

HOY_HONDURAS = date(2026, 9, 26)


def _crear_cuenta(
    account_service,
    session_factory,
    actor,
    *,
    party_id,
    kind=AccountKind.PAYABLE,
    amount=Decimal("1000.00"),
    due_date=date(2026, 10, 10),
    source_id="1",
) -> int:
    def _op(session):
        return account_service.create_account(
            session,
            actor,
            kind=kind,
            party_id=party_id,
            source_type="purchase",
            source_id=source_id,
            amount=amount,
            due_date=due_date,
        )

    return run_in_transaction(session_factory, _op)


def _pago(amount: str, *, method=PaymentMethod.EFECTIVO, reference=None) -> PaymentInput:
    return PaymentInput(method=method, amount=Decimal(amount), reference=reference)


def test_dos_abonos_saldan_exacto(account_service, session_factory, admin_actor, proveedor_id):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    account_service.pay(admin_actor, cuenta_id, _pago("333.33"), "req-1")
    vista = account_service.pay(admin_actor, cuenta_id, _pago("666.67"), "req-2")

    assert vista.balance == Decimal("0.00")
    assert vista.status == AccountStatus.PAGADA
    assert len(vista.payments) == 2


def test_abono_excede_saldo_falla(account_service, session_factory, admin_actor, proveedor_id):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    with pytest.raises(OverpaymentError):
        account_service.pay(admin_actor, cuenta_id, _pago("1000.01"), "req-1")


def test_abono_cero_o_negativo_rechazado_por_payment_input():
    with pytest.raises(PydanticValidationError):
        PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("0"))
    with pytest.raises(PydanticValidationError):
        PaymentInput(method=PaymentMethod.EFECTIVO, amount=Decimal("-1"))


def test_reintento_con_mismo_request_id_no_duplica(
    account_service, session_factory, admin_actor, proveedor_id
):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    primero = account_service.pay(admin_actor, cuenta_id, _pago("300.00"), "req-1")
    segundo = account_service.pay(admin_actor, cuenta_id, _pago("300.00"), "req-1")

    assert primero.balance == segundo.balance == Decimal("700.00")
    assert len(segundo.payments) == 1

    with session_factory() as session:
        abonos = session.query(AccountPayment).filter_by(account_id=cuenta_id).all()
        assert len(abonos) == 1


def test_request_id_reutilizado_en_otra_cuenta_falla(
    account_service, session_factory, admin_actor, proveedor_id
):
    cuenta_a = _crear_cuenta(
        account_service, session_factory, admin_actor, party_id=proveedor_id, source_id="1"
    )
    cuenta_b = _crear_cuenta(
        account_service, session_factory, admin_actor, party_id=proveedor_id, source_id="2"
    )
    account_service.pay(admin_actor, cuenta_a, _pago("100.00"), "req-1")
    with pytest.raises(RequestIdReused):
        account_service.pay(admin_actor, cuenta_b, _pago("100.00"), "req-1")


def test_vencida_por_reloj(account_service, session_factory, admin_actor, proveedor_id):
    cuenta_id = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        due_date=date(2026, 9, 25),
    )
    vista = account_service.get(admin_actor, cuenta_id)
    assert vista.status == AccountStatus.VENCIDA
    assert vista.days_overdue == 1


def test_pendiente_cuando_no_ha_vencido(
    account_service, session_factory, admin_actor, proveedor_id
):
    cuenta_id = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        due_date=date(2026, 9, 26),
    )
    vista = account_service.get(admin_actor, cuenta_id)
    assert vista.status == AccountStatus.PENDIENTE


def test_pagada_cuando_saldo_es_cero(account_service, session_factory, admin_actor, proveedor_id):
    cuenta_id = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        due_date=date(2026, 9, 1),
        amount=Decimal("50.00"),
    )
    account_service.pay(admin_actor, cuenta_id, _pago("50.00"), "req-1")
    vista = account_service.get(admin_actor, cuenta_id)
    assert vista.status == AccountStatus.PAGADA


def test_reconciliacion_balance_vs_abonos(
    account_service, session_factory, admin_actor, proveedor_id
):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    account_service.pay(admin_actor, cuenta_id, _pago("400.00"), "req-1")
    account_service.pay(admin_actor, cuenta_id, _pago("100.00"), "req-2")

    with session_factory() as session:
        assert account_service.reconcile(session, cuenta_id) is True


def test_update_directo_de_abono_falla(account_service, session_factory, admin_actor, proveedor_id):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    account_service.pay(admin_actor, cuenta_id, _pago("100.00"), "req-1")

    with session_factory() as session:
        abono_id = session.query(AccountPayment).filter_by(account_id=cuenta_id).one().id

    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE com_account_payment SET amount = 999 WHERE id = :id"), {"id": abono_id}
        )
        session.commit()

    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(text("DELETE FROM com_account_payment WHERE id = :id"), {"id": abono_id})
        session.commit()


def test_check_balance_negativo_a_nivel_sql(
    account_service, session_factory, admin_actor, proveedor_id
):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    with session_factory() as session, pytest.raises(DBAPIError):
        session.execute(
            text("UPDATE com_account SET balance = -1 WHERE id = :id"), {"id": cuenta_id}
        )
        session.commit()


def test_bodega_con_cxp_pagar_puede_pagar_payable_pero_no_cobrar_receivable(
    account_service,
    session_factory,
    admin_actor,
    bodega_pagador_actor,
    proveedor_id,
    cliente_id,
):
    cuenta_pagar = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        kind=AccountKind.PAYABLE,
    )
    cuenta_cobrar = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=cliente_id,
        kind=AccountKind.RECEIVABLE,
        source_id="9",
    )

    vista = account_service.pay(bodega_pagador_actor, cuenta_pagar, _pago("100.00"), "req-1")
    assert vista.balance == Decimal("900.00")

    with pytest.raises(PermissionDenied):
        account_service.pay(bodega_pagador_actor, cuenta_cobrar, _pago("100.00"), "req-2")


def test_vendedor_sin_permiso_no_puede_pagar(
    account_service, session_factory, admin_actor, vendedor_actor, proveedor_id
):
    cuenta_id = _crear_cuenta(account_service, session_factory, admin_actor, party_id=proveedor_id)
    with pytest.raises(PermissionDenied):
        account_service.pay(vendedor_actor, cuenta_id, _pago("100.00"), "req-1")


def test_vendedor_puede_ver_cuentas_por_cobrar(
    account_service, session_factory, admin_actor, vendedor_actor, cliente_id
):
    cuenta_id = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=cliente_id,
        kind=AccountKind.RECEIVABLE,
    )
    vista = account_service.get(vendedor_actor, cuenta_id)
    assert vista.id == cuenta_id


def test_get_cuenta_inexistente_falla(account_service, admin_actor):
    with pytest.raises(NotFound):
        account_service.get(admin_actor, 999)


def test_monto_no_positivo_rechazado_en_create_account(
    account_service, session_factory, admin_actor, proveedor_id
):
    def _op(session):
        account_service.create_account(
            session,
            admin_actor,
            kind=AccountKind.PAYABLE,
            party_id=proveedor_id,
            source_type="purchase",
            source_id="1",
            amount=Decimal("0"),
            due_date=date(2026, 10, 10),
        )

    with pytest.raises(ValidationError):
        run_in_transaction(session_factory, _op)


def test_contraparte_inactiva_rechazada_en_create_account(
    account_service, session_factory, admin_actor, party_service, proveedor_id
):
    party_service.set_active(admin_actor, proveedor_id, False)

    def _op(session):
        account_service.create_account(
            session,
            admin_actor,
            kind=AccountKind.PAYABLE,
            party_id=proveedor_id,
            source_type="purchase",
            source_id="1",
            amount=Decimal("100"),
            due_date=date(2026, 10, 10),
        )

    with pytest.raises(ValidationError):
        run_in_transaction(session_factory, _op)


def test_list_filtra_por_estado_y_texto(
    account_service, session_factory, admin_actor, proveedor_id, party_service
):
    otro_proveedor_id = party_service.create(
        admin_actor,
        PartyInput(kind=PartyKind.NEGOCIO, name="Refaccionaria Central", is_supplier=True),
    )
    vencida_id = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        due_date=date(2026, 9, 1),
        source_id="1",
    )
    pendiente_id = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=otro_proveedor_id,
        due_date=date(2026, 12, 1),
        source_id="2",
    )

    solo_vencidas = account_service.list(
        admin_actor, AccountKind.PAYABLE, status=AccountStatus.VENCIDA
    )
    assert [c.id for c in solo_vencidas.items] == [vencida_id]

    por_texto = account_service.list(admin_actor, AccountKind.PAYABLE, text="refaccionaria")
    assert [c.id for c in por_texto.items] == [pendiente_id]


def test_party_balance_suma_cuentas_del_proveedor(
    account_service, session_factory, admin_actor, proveedor_id
):
    _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        amount=Decimal("100"),
        source_id="1",
    )
    cuenta_2 = _crear_cuenta(
        account_service,
        session_factory,
        admin_actor,
        party_id=proveedor_id,
        amount=Decimal("200"),
        source_id="2",
    )
    account_service.pay(admin_actor, cuenta_2, _pago("50.00"), "req-1")

    saldo = account_service.party_balance(admin_actor, proveedor_id, AccountKind.PAYABLE)
    assert saldo == Decimal("250.00")


def test_uso_directo_del_modelo_account_disponible_para_migracion():
    # La migración de la fase reutiliza el modelo y los disparadores literalmente.
    assert Account.__tablename__ == "com_account"
