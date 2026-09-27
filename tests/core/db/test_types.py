"""Pruebas de los TypeDecorator de dinero/cantidad (ADR-002)."""

from decimal import Decimal

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select

from sistemashn.core.db.types import Money, Quantity, Rate, UnitCost


@pytest.fixture
def engine():
    eng = create_engine("sqlite://")
    yield eng
    eng.dispose()


@pytest.fixture
def tabla(engine):
    meta = MetaData()
    t = Table(
        "valores",
        meta,
        Column("id", Integer, primary_key=True),
        Column("monto", Money),
        Column("costo", UnitCost),
        Column("cantidad", Quantity),
        Column("tasa", Rate),
    )
    meta.create_all(engine)
    return t


def test_cache_ok() -> None:
    assert Money().cache_ok is True
    assert UnitCost().cache_ok is True
    assert Quantity().cache_ok is True
    assert Rate().cache_ok is True


def test_ida_y_vuelta_decimales(engine, tabla) -> None:
    with engine.begin() as conn:
        conn.execute(
            tabla.insert().values(
                monto=Decimal("10.005"),
                costo=Decimal("1.00005"),
                cantidad=Decimal("2.0005"),
                tasa=Decimal("0.15"),
            )
        )
        row = conn.execute(select(tabla)).one()
    assert row.monto == Decimal("10.01")
    assert row.costo == Decimal("1.0001")
    assert row.cantidad == Decimal("2.001")
    assert row.tasa == Decimal("0.1500")


def test_negativos_y_grandes(engine, tabla) -> None:
    with engine.begin() as conn:
        conn.execute(
            tabla.insert().values(
                monto=Decimal("-999999999.99"),
                costo=Decimal("-1.2345"),
                cantidad=Decimal("-100.500"),
                tasa=Decimal("0.1800"),
            )
        )
        row = conn.execute(select(tabla)).one()
    assert row.monto == Decimal("-999999999.99")
    assert row.costo == Decimal("-1.2345")
    assert row.cantidad == Decimal("-100.500")
    assert row.tasa == Decimal("0.1800")


def test_acepta_int_y_str(engine, tabla) -> None:
    with engine.begin() as conn:
        conn.execute(tabla.insert().values(monto="10", costo="1", cantidad=5, tasa="0.15"))
        row = conn.execute(select(tabla)).one()
    assert row.monto == Decimal("10.00")
    assert row.costo == Decimal("1.0000")
    assert row.cantidad == Decimal("5.000")
    assert row.tasa == Decimal("0.1500")


def test_none_pasa(engine, tabla) -> None:
    with engine.begin() as conn:
        conn.execute(tabla.insert().values(id=1, monto=None, costo=None, cantidad=None, tasa=None))
        row = conn.execute(select(tabla)).one()
    assert row.monto is None
    assert row.costo is None
    assert row.cantidad is None
    assert row.tasa is None


def test_rechaza_float() -> None:
    with pytest.raises(TypeError):
        Money().process_bind_param(10.5, None)
    with pytest.raises(TypeError):
        UnitCost().process_bind_param(1.5, None)
    with pytest.raises(TypeError):
        Quantity().process_bind_param(1.5, None)
    with pytest.raises(TypeError):
        Rate().process_bind_param(0.15, None)


def test_utc_datetime_ida_y_vuelta_aware() -> None:
    from datetime import UTC, datetime, timedelta, timezone

    from sistemashn.core.db.types import UtcDateTime

    t = UtcDateTime()
    honduras = timezone(timedelta(hours=-6))
    stored = t.process_bind_param(datetime(2026, 9, 26, 9, 0, tzinfo=honduras), None)
    assert stored == datetime(2026, 9, 26, 15, 0)
    assert t.process_result_value(stored, None) == datetime(2026, 9, 26, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        t.process_bind_param(datetime(2026, 9, 26, 9, 0), None)


def test_escape_like() -> None:
    from sistemashn.core.db.text import escape_like

    bs = "\\"
    assert escape_like("10%_a" + bs) == "10" + bs + "%" + bs + "_a" + bs + bs
