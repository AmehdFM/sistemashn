"""Normalización de número de parte y proveedor de búsqueda extensible (plan T2.4)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from sistemashn.comercial.catalogo.models import Product
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.repuestos.partes.models import Part

_CARACTERES_IGNORADOS = (" ", "-", ".", "/")


def normalize_part_number(text: str) -> str:
    """Mayúsculas sin espacios, guiones, puntos ni barras."""
    resultado = text.strip().upper()
    for caracter in _CARACTERES_IGNORADOS:
        resultado = resultado.replace(caracter, "")
    return resultado


class RepuestosSearchProvider:
    """Coincidencias de búsqueda por número de parte, incluyendo equivalentes."""

    def search(self, session: Session, text: str, limit: int) -> list[int]:
        norm = normalize_part_number(text)
        if len(norm) < 3:
            return []

        coincidencias = session.scalars(
            select(Part).where(
                Part.part_number_search.like(f"%{escape_like(norm)}%", escape=LIKE_ESCAPE)
            )
        ).all()
        if not coincidencias:
            return []

        grupos = {p.equivalence_group_id for p in coincidencias if p.equivalence_group_id}
        ids_candidatos: set[int] = {p.product_id for p in coincidencias}
        if grupos:
            equivalentes = session.scalars(
                select(Part).where(Part.equivalence_group_id.in_(grupos))
            ).all()
            ids_candidatos.update(p.product_id for p in equivalentes)

        activos = session.scalars(
            select(Product.id).where(Product.id.in_(ids_candidatos), Product.active.is_(True))
        ).all()
        return sorted(activos)[:limit]
