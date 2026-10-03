"""Proveedor de búsqueda comercial para marca, especificación y empaque."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from sistemashn.comercial.catalogo.search import normalize_search
from sistemashn.core.db.text import LIKE_ESCAPE, escape_like
from sistemashn.ferreteria.catalogo.models import FerItem, FerPack


class FerreteriaSearchProvider:
    """Devuelve solo el SKU dueño de cada coincidencia de presentación."""

    def search(self, session: Session, text: str, limit: int) -> list[int]:
        term = text.strip()
        if not term or limit <= 0:
            return []
        ids: list[int] = []

        packs = session.scalars(
            select(FerPack)
            .where(
                FerPack.active.is_(True),
                FerPack.code.like(f"%{escape_like(term)}%", escape=LIKE_ESCAPE),
            )
            .order_by(FerPack.code)
        )
        for pack in packs:
            if pack.product_id not in ids:
                ids.append(pack.product_id)
                if len(ids) >= limit:
                    return ids

        normalized = normalize_search(term)
        for item in session.scalars(select(FerItem).order_by(FerItem.product_id)):
            attributes = " ".join((item.brand or "", item.family or "", item.specs or ""))
            if normalized in normalize_search(attributes) and item.product_id not in ids:
                ids.append(item.product_id)
                if len(ids) >= limit:
                    return ids
        return ids
