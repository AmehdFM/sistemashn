"""Definición del módulo Repuestos: permisos, perfiles y pantallas (plan T2.4)."""

from sistemashn.core.modules.contracts import ModuleDef, PermissionDef, ProfileDef, ScreenDef

_GRUPO_REPUESTOS = "Repuestos"

_PERMISOS = (
    PermissionDef("rep.partes.gestionar", "Gestionar partes y compatibilidad", _GRUPO_REPUESTOS),
    PermissionDef("rep.vehiculos.gestionar", "Gestionar marcas y modelos", _GRUPO_REPUESTOS),
)

_PERFIL_REPUESTOS_BODEGA = ProfileDef(
    code="repuestos_bodega",
    label="Bodega de repuestos",
    permissions=frozenset(
        {
            "com.catalogo.ver",
            "com.catalogo.gestionar",
            "com.catalogo.importar",
            "com.inventario.ver",
            "com.inventario.ajustar",
            "rep.partes.gestionar",
            "rep.vehiculos.gestionar",
        }
    ),
)

_PANTALLAS = (
    ScreenDef(
        route="/repuestos/vehiculos",
        label="Vehículos",
        icon="DIRECTIONS_CAR",
        permission="rep.vehiculos.gestionar",
        group=_GRUPO_REPUESTOS,
        order=1,
    ),
    ScreenDef(
        route="/repuestos/compatibles",
        label="Buscar por vehículo",
        icon="SEARCH",
        permission="com.catalogo.ver",
        group=_GRUPO_REPUESTOS,
        order=2,
    ),
)

REPUESTOS_MODULE = ModuleDef(
    code="repuestos",
    label="Repuestos",
    permissions=_PERMISOS,
    profiles=(_PERFIL_REPUESTOS_BODEGA,),
    screens=_PANTALLAS,
)
