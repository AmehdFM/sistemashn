"""Normalización de texto de búsqueda y protocolo extensible de proveedores (plan T2.1)."""

import unicodedata
from typing import Protocol

from sqlalchemy.orm import Session


def normalize_search(text: str) -> str:
    """Minúsculas y sin acentos/diacríticos, para indexar/buscar por nombre."""
    sin_acentos = unicodedata.normalize("NFKD", text)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return sin_acentos.lower().strip()


class ProductSearchProvider(Protocol):
    """Proveedor externo de coincidencias de búsqueda (p. ej. Repuestos por número de parte)."""

    def search(self, session: Session, text: str, limit: int) -> list[int]:
        """Devuelve ids de `com_product` que coinciden con `text`, hasta `limit`."""
        ...
