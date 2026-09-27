"""Pruebas de `format_local_datetime` (UTC -> Honduras UTC-6)."""

from datetime import UTC, datetime

from sistemashn.core.ui.views import format_local_datetime


def test_format_local_datetime_convierte_utc_a_honduras():
    dt = datetime(2026, 9, 27, 18, 30, tzinfo=UTC)

    assert format_local_datetime(dt) == "27/09/2026 12:30"


def test_format_local_datetime_cruza_medianoche():
    dt = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)

    assert format_local_datetime(dt) == "26/09/2026 21:00"


def test_format_local_datetime_asume_utc_si_es_naive():
    dt = datetime(2026, 9, 27, 18, 30)

    assert format_local_datetime(dt) == "27/09/2026 12:30"
