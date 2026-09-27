"""Pruebas de sistemashn.core.money (ADR-002)."""

from decimal import Decimal

import pytest

from sistemashn.core.money import ZERO, money, qty, rate, unit_cost


class TestMoney:
    def test_cuantiza_a_2_decimales(self) -> None:
        assert money("10") == Decimal("10.00")
        assert money(Decimal("10.005")) == Decimal("10.01")

    def test_half_up_redondea_hacia_arriba(self) -> None:
        assert money("0.005") == Decimal("0.01")
        assert money("2.675") == Decimal("2.68")

    def test_acepta_decimal_int_str(self) -> None:
        assert money(5) == Decimal("5.00")
        assert money("5.5") == Decimal("5.50")
        assert money(Decimal("5.5")) == Decimal("5.50")

    def test_rechaza_float(self) -> None:
        with pytest.raises(TypeError):
            money(5.5)  # type: ignore[arg-type]

    def test_negativos_y_grandes(self) -> None:
        assert money("-10.005") == Decimal("-10.01")
        assert money("999999999.99") == Decimal("999999999.99")


class TestUnitCost:
    def test_cuantiza_a_4_decimales(self) -> None:
        assert unit_cost("1.00005") == Decimal("1.0001")

    def test_rechaza_float(self) -> None:
        with pytest.raises(TypeError):
            unit_cost(1.5)  # type: ignore[arg-type]


class TestQty:
    def test_cuantiza_a_3_decimales(self) -> None:
        assert qty("1.0005") == Decimal("1.001")

    def test_rechaza_float(self) -> None:
        with pytest.raises(TypeError):
            qty(1.5)  # type: ignore[arg-type]


class TestRate:
    def test_cuantiza_a_4_decimales(self) -> None:
        assert rate("0.15") == Decimal("0.1500")
        assert rate("0.180000005") == Decimal("0.1800")

    def test_rechaza_float(self) -> None:
        with pytest.raises(TypeError):
            rate(0.15)  # type: ignore[arg-type]


def test_zero_constante() -> None:
    assert Decimal("0") == ZERO
