"""Contexto compartido de la aplicación de escritorio (T1.6a)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from sistemashn.core.authorization.actor import Actor
from sistemashn.core.authorization.service import Authorizer
from sistemashn.core.modules.contracts import ModuleRegistry


@dataclass
class AppContext:
    """Dependencias que necesitan las pantallas de la UI para funcionar."""

    session_factory: sessionmaker[Session]
    registry: ModuleRegistry
    authorizer: Authorizer
    services: dict[str, object] = field(default_factory=dict)
    clock: Callable[[], datetime] | None = None
    data_dir: Path | None = None
    actor: Actor | None = None
    business_name: str = "SistemasHN"
    logo_path: Path | None = None

    def service(self, name: str) -> Any:
        """Devuelve el servicio registrado bajo `name` o lanza KeyError explicativo."""
        try:
            return self.services[name]
        except KeyError as exc:
            raise KeyError(f"servicio no registrado en AppContext: '{name}'") from exc
