"""TypeDecorators de SQLAlchemy para dinero/cantidades exactas (ADR-002).

Cada valor se guarda en SQLite como INTEGER escalado. `process_bind_param` cuantiza
con los helpers de `sistemashn.core.money` (ROUND_HALF_UP) y convierte a entero;
`process_result_value` reconstruye el `Decimal` cuantizado. `float` está prohibido.
"""

from datetime import UTC
from decimal import Decimal

from sqlalchemy import DateTime, Integer
from sqlalchemy.types import TypeDecorator

from sistemashn.core.money import money, qty, rate, unit_cost


class _ScaledDecimal(TypeDecorator):
    """Base: entero escalado <-> Decimal cuantizado."""

    impl = Integer
    cache_ok = True
    _scale: int
    _quantize = staticmethod(money)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError("float no permitido: use Decimal, int o str")
        quantizado = self._quantize(value)
        return int(quantizado * self._scale)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self._quantize(Decimal(value) / self._scale)


class Money(_ScaledDecimal):
    cache_ok = True
    """Importes en Lempiras: 2 decimales (centavos)."""

    _scale = 100
    _quantize = staticmethod(money)


class UnitCost(_ScaledDecimal):
    cache_ok = True
    """Costo unitario / costo promedio ponderado: 4 decimales."""

    _scale = 10_000
    _quantize = staticmethod(unit_cost)


class Quantity(_ScaledDecimal):
    cache_ok = True
    """Cantidades: 3 decimales."""

    _scale = 1_000
    _quantize = staticmethod(qty)


class Rate(_ScaledDecimal):
    cache_ok = True
    """Tasas (p. ej. ISV 0.15): 4 decimales."""

    _scale = 10_000
    _quantize = staticmethod(rate)


class UtcDateTime(TypeDecorator):
    """Fecha/hora siempre en UTC y *aware*.

    SQLite no conserva la zona horaria: al guardar se exige un datetime aware y se convierte a
    UTC; al leer se devuelve con `tzinfo=UTC`. Un datetime naive se rechaza con ValueError para
    evitar mezclar horas locales con UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime sin zona horaria: use datetimes aware (UTC)")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)
