"""Pruebas de idempotencia de operaciones (plan T3.1)."""

import pytest

from sistemashn.comercial import idempotency
from sistemashn.core.errors import ValidationError


def test_find_previous_sin_registro_devuelve_none(session_factory) -> None:
    with session_factory() as session:
        assert idempotency.find_previous(session, "req-1", "compra.confirmar") is None


def test_remember_y_find_previous_devuelven_el_mismo_resultado(session_factory, clock) -> None:
    with session_factory() as session:
        idempotency.remember(session, "req-1", "compra.confirmar", "C-000001", clock)
        session.commit()

    with session_factory() as session:
        resultado = idempotency.find_previous(session, "req-1", "compra.confirmar")
        assert resultado == "C-000001"


def test_mismo_request_id_con_otra_operacion_falla(session_factory, clock) -> None:
    with session_factory() as session:
        idempotency.remember(session, "req-1", "compra.confirmar", "C-000001", clock)
        session.commit()

    with session_factory() as session, pytest.raises(ValidationError):
        idempotency.find_previous(session, "req-1", "cxp.pagar")
