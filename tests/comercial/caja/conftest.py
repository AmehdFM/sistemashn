"""Fixtures locales de las pruebas de caja (plan T4.3)."""

import pytest

from sistemashn.comercial.caja.service import CashService


@pytest.fixture
def cash_service(session_factory, authorizer, clock) -> CashService:
    return CashService(session_factory, authorizer, clock=clock)
