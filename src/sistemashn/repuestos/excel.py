"""Extensión de columnas de Excel de Repuestos: `numero_parte`, `fabricante`, `origen` (T2.6b).

Se ejecuta dentro de la transacción del importador (`ExcelImportService.commit`): no abre
transacción propia ni verifica permisos (eso ya lo hizo el importador).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from sistemashn.core.authorization.actor import Actor
from sistemashn.repuestos.partes.models import Part
from sistemashn.repuestos.partes.search import normalize_part_number

_ORIGENES_VALIDOS = ("original", "generico")


class RepuestosExcelExtension:
    """Hook `ExcelColumnExtension` que agrega datos de repuesto al catálogo importado."""

    columns: tuple[str, ...] = ("numero_parte", "fabricante", "origen")

    def validate(self, row: dict[str, Any]) -> list[str]:
        numero = str(row.get("numero_parte") or "").strip()
        if not numero:
            return []  # sin número de parte: fila normal de Comercial, no se toca

        origen = str(row.get("origen") or "").strip().lower()
        if origen and origen not in _ORIGENES_VALIDOS:
            return [f"origen inválido: '{origen}' (use original o generico)"]
        return []

    def apply(self, session: Session, actor: Actor, product_id: int, row: dict[str, Any]) -> None:
        numero = str(row.get("numero_parte") or "").strip()
        if not numero:
            return

        fabricante = row.get("fabricante")
        fabricante = str(fabricante).strip() or None if fabricante not in (None, "") else None
        origen = str(row.get("origen") or "").strip().lower() or "generico"

        parte = session.get(Part, product_id)
        if parte is None:
            parte = Part(
                product_id=product_id,
                part_number=numero,
                part_number_search=normalize_part_number(numero),
                manufacturer=fabricante,
                origin=origen,
            )
            session.add(parte)
        else:
            parte.part_number = numero
            parte.part_number_search = normalize_part_number(numero)
            parte.manufacturer = fabricante
            parte.origin = origen
        session.flush()

    def export(self, session: Session, product_id: int) -> dict[str, Any]:
        parte = session.get(Part, product_id)
        if parte is None:
            return {"numero_parte": "", "fabricante": "", "origen": ""}
        return {
            "numero_parte": parte.part_number,
            "fabricante": parte.manufacturer or "",
            "origen": parte.origin,
        }
