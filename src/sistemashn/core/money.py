"""Helpers de dinero exacto (ADR-002): siempre Decimal, nunca float."""

from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")

_MONEY_QUANT = Decimal("0.01")
_UNIT_COST_QUANT = Decimal("0.0001")
_QTY_QUANT = Decimal("0.001")
_RATE_QUANT = Decimal("0.0001")


def _to_decimal(v: Decimal | int | str) -> Decimal:
    if isinstance(v, float):
        raise TypeError("float no permitido: use Decimal, int o str")
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, str):
        return Decimal(v)
    raise TypeError(f"tipo no soportado: {type(v)!r}")


def money(v: Decimal | int | str) -> Decimal:
    """Cuantiza a 2 decimales (centavos) con ROUND_HALF_UP."""
    return _to_decimal(v).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def unit_cost(v: Decimal | int | str) -> Decimal:
    """Cuantiza a 4 decimales (costo unitario/promedio ponderado)."""
    return _to_decimal(v).quantize(_UNIT_COST_QUANT, rounding=ROUND_HALF_UP)


def qty(v: Decimal | int | str) -> Decimal:
    """Cuantiza a 3 decimales (cantidades)."""
    return _to_decimal(v).quantize(_QTY_QUANT, rounding=ROUND_HALF_UP)


def rate(v: Decimal | int | str) -> Decimal:
    """Cuantiza a 4 decimales (tasas, p. ej. ISV 0.15 -> 0.1500)."""
    return _to_decimal(v).quantize(_RATE_QUANT, rounding=ROUND_HALF_UP)
