"""Definición del módulo Core: permisos, perfil administrador y pantallas (plan T1.1)."""

from sistemashn.core.modules.contracts import ModuleDef, PermissionDef, ProfileDef, ScreenDef

_GRUPO_ADMIN = "Administración"

_PERMISOS = (
    PermissionDef("core.usuarios.ver", "Ver usuarios", _GRUPO_ADMIN),
    PermissionDef("core.usuarios.gestionar", "Gestionar usuarios", _GRUPO_ADMIN, sensitive=True),
    PermissionDef("core.auditoria.ver", "Ver auditoría", _GRUPO_ADMIN),
    PermissionDef(
        "core.ajustes.gestionar", "Gestionar ajustes del negocio", _GRUPO_ADMIN, sensitive=True
    ),
    PermissionDef("core.respaldos.gestionar", "Gestionar respaldos", _GRUPO_ADMIN, sensitive=True),
    PermissionDef(
        "core.actualizaciones.gestionar",
        "Gestionar actualizaciones",
        _GRUPO_ADMIN,
        sensitive=True,
    ),
    PermissionDef("core.licencia.ver", "Ver licencia", _GRUPO_ADMIN),
)

_PERFIL_ADMINISTRADOR = ProfileDef(
    code="administrador",
    label="Administrador",
    permissions=frozenset(p.code for p in _PERMISOS),
)

_PANTALLAS = (
    ScreenDef(
        route="/usuarios",
        label="Usuarios",
        icon="PEOPLE",
        permission="core.usuarios.ver",
        group=_GRUPO_ADMIN,
        order=1,
    ),
    ScreenDef(
        route="/auditoria",
        label="Auditoría",
        icon="HISTORY",
        permission="core.auditoria.ver",
        group=_GRUPO_ADMIN,
        order=2,
    ),
    ScreenDef(
        route="/ajustes",
        label="Ajustes",
        icon="SETTINGS",
        permission="core.ajustes.gestionar",
        group=_GRUPO_ADMIN,
        order=3,
    ),
    ScreenDef(
        route="/respaldos",
        label="Respaldos",
        icon="BACKUP",
        permission="core.respaldos.gestionar",
        group=_GRUPO_ADMIN,
        order=4,
    ),
    ScreenDef(
        route="/licencia",
        label="Licencia",
        icon="VERIFIED_USER",
        permission="core.licencia.ver",
        group=_GRUPO_ADMIN,
        order=5,
    ),
)

CORE_MODULE = ModuleDef(
    code="core",
    label="Core",
    permissions=_PERMISOS,
    profiles=(_PERFIL_ADMINISTRADOR,),
    screens=_PANTALLAS,
)
