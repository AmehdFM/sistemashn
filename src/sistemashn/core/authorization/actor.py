"""Identidad del usuario que ejecuta una operación de servicio."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    user_id: int
    username: str
    is_admin: bool
    session_id: str


# Solo para tareas internas (primer arranque, migraciones); nunca para acciones de un empleado.
SYSTEM_ACTOR = Actor(user_id=0, username="sistema", is_admin=True, session_id="system")
