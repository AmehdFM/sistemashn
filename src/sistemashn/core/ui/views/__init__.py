"""Vistas de administración del Core (T1.6b-2) y helpers compartidos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

# Honduras no observa horario de verano: desplazamiento fijo UTC-6.
_HONDURAS_TZ = timezone(timedelta(hours=-6))


def format_local_datetime(dt: datetime) -> str:
    """Formatea `dt` (UTC o naive-asumido-UTC) en hora local de Honduras `dd/mm/aaaa hh:mm`."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local = dt.astimezone(_HONDURAS_TZ)
    return local.strftime("%d/%m/%Y %H:%M")
