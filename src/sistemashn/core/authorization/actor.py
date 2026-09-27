"""Identidad del usuario que ejecuta una operación de servicio."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    user_id: int
    username: str
    is_admin: bool
    session_id: str
    #: Perfil del usuario al momento de iniciar sesión (T7.6: decide `home_route` y modo
    #: mostrador por defecto en la UI). No se usa para autorizar: eso siempre relee el
    #: perfil vigente en base de datos, ya que este valor puede quedar desactualizado si
    #: el perfil del usuario cambia durante la sesión.
    profile_code: str | None = None


# Solo para tareas internas (primer arranque, migraciones); nunca para acciones de un empleado.
SYSTEM_ACTOR = Actor(user_id=0, username="sistema", is_admin=True, session_id="system")
