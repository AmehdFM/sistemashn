"""Numeración interna consecutiva de documentos (plan T3.1).

`next_number` debe llamarse dentro de la transacción del documento: si esta se revierte, el
número no se consume (no hay commit parcial posible con SQLite + `BEGIN IMMEDIATE`).
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from sistemashn.core.db.base import Base


class Sequence(Base):
    """Contador consecutivo nombrado, p. ej. 'compra'."""

    __tablename__ = "com_sequence"

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    next_value: Mapped[int] = mapped_column(Integer, nullable=False)


def next_number(session: Session, name: str) -> int:
    """Devuelve el siguiente número de `name`, creando el contador en 1 si no existe."""
    secuencia = session.get(Sequence, name)
    if secuencia is None:
        secuencia = Sequence(name=name, next_value=1)
        session.add(secuencia)
        session.flush()
    numero = secuencia.next_value
    secuencia.next_value = numero + 1
    session.flush()
    return numero


def format_number(prefix: str, n: int, width: int = 6) -> str:
    """Formatea un número de secuencia como `PREFIJO-000123`."""
    return f"{prefix}-{n:0{width}d}"
