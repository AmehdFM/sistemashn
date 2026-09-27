"""Ventas en espera del POS: borradores en memoria, no persistidos (T7.5).

Nada aparcado toca inventario ni caja hasta confirmarse, así que perder esta lista si la
aplicación se cierra sin retomar/confirmar un borrador es un riesgo aceptado explícitamente
(ver plan de Fase 7, T7.5).
"""

from __future__ import annotations

import copy
from uuid import uuid4


class ParkedSalesStore:
    """Guarda borradores de venta (`dict` serializable) en memoria, por usuario."""

    def __init__(self) -> None:
        self._borradores: dict[str, tuple[int, dict]] = {}

    def park(self, user_id: int, borrador: dict) -> str:
        """Guarda una copia de `borrador` y retorna el id generado para retomarlo luego."""
        park_id = uuid4().hex
        self._borradores[park_id] = (user_id, copy.deepcopy(borrador))
        return park_id

    def list_for_user(self, user_id: int) -> list[tuple[str, dict]]:
        """Borradores del usuario, en orden de creación."""
        return [
            (park_id, borrador)
            for park_id, (uid, borrador) in self._borradores.items()
            if uid == user_id
        ]

    def retrieve(self, park_id: str) -> dict | None:
        """Copia del borrador guardado bajo `park_id`, o `None` si no existe."""
        entrada = self._borradores.get(park_id)
        return copy.deepcopy(entrada[1]) if entrada is not None else None

    def discard(self, park_id: str) -> None:
        """Descarta el borrador; no lanza si `park_id` no existe."""
        self._borradores.pop(park_id, None)
