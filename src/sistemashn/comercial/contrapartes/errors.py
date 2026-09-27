"""Errores propios de contrapartes (plan T3.1)."""

from dataclasses import dataclass

from sistemashn.core.errors import ValidationError


@dataclass(frozen=True)
class PartyRef:
    """Referencia liviana a una contraparte, usada como candidato de duplicado."""

    id: int
    name: str
    rtn: str | None


class PossibleDuplicate(ValidationError):
    """Existen contrapartes similares (mismo RTN o mismo nombre normalizado).

    El servicio nunca fusiona automáticamente: quien llama debe revisar `candidates` y, si
    confirma que no es un duplicado, reintentar con `allow_duplicate=True`.
    """

    def __init__(self, candidates: list[PartyRef]) -> None:
        self.candidates = candidates
        nombres = ", ".join(f"{c.name} (#{c.id})" for c in candidates)
        super().__init__(f"posibles contrapartes duplicadas: {nombres}")
