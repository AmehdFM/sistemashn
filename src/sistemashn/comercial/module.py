"""Definición del módulo Comercial: permisos, perfiles y pantallas (plan T2.1)."""

from sistemashn.core.modules.contracts import ModuleDef, PermissionDef, ProfileDef, ScreenDef

_GRUPO_CATALOGO = "Catálogo"
_GRUPO_INVENTARIO = "Inventario"
_GRUPO_COMPRAS = "Compras"
_GRUPO_VENTAS = "Ventas"

_PERMISOS = (
    PermissionDef("com.catalogo.ver", "Ver catálogo", _GRUPO_CATALOGO),
    PermissionDef("com.catalogo.gestionar", "Gestionar catálogo", _GRUPO_CATALOGO),
    PermissionDef("com.catalogo.importar", "Importar catálogo desde Excel", _GRUPO_CATALOGO),
    PermissionDef("com.costos.ver", "Ver costos", _GRUPO_CATALOGO, sensitive=True),
    PermissionDef("com.inventario.ver", "Ver inventario", _GRUPO_INVENTARIO),
    PermissionDef("com.inventario.ajustar", "Ajustar inventario", _GRUPO_INVENTARIO),
    PermissionDef("com.contrapartes.ver", "Ver contrapartes", _GRUPO_COMPRAS),
    PermissionDef("com.contrapartes.gestionar", "Gestionar contrapartes", _GRUPO_COMPRAS),
    PermissionDef("com.compras.ver", "Ver compras", _GRUPO_COMPRAS),
    PermissionDef("com.compras.registrar", "Registrar compras", _GRUPO_COMPRAS),
    PermissionDef("com.cxp.ver", "Ver cuentas por pagar", _GRUPO_COMPRAS),
    PermissionDef("com.cxp.pagar", "Pagar cuentas por pagar", _GRUPO_COMPRAS),
    PermissionDef("com.cxc.ver", "Ver cuentas por cobrar", _GRUPO_VENTAS),
    PermissionDef("com.cxc.cobrar", "Cobrar cuentas por cobrar", _GRUPO_VENTAS),
)

_PERFIL_VENDEDOR = ProfileDef(
    code="vendedor",
    label="Vendedor",
    permissions=frozenset({"com.catalogo.ver", "com.inventario.ver", "com.cxc.ver"}),
)

_PERFIL_BODEGA = ProfileDef(
    code="bodega",
    label="Bodega",
    permissions=frozenset(
        {
            "com.catalogo.ver",
            "com.catalogo.gestionar",
            "com.catalogo.importar",
            "com.inventario.ver",
            "com.inventario.ajustar",
            "com.contrapartes.ver",
            "com.contrapartes.gestionar",
            "com.compras.ver",
            "com.compras.registrar",
        }
    ),
)

_PERFIL_GERENTE = ProfileDef(
    code="gerente",
    label="Gerente",
    permissions=frozenset(p.code for p in _PERMISOS),
)

_PANTALLAS = (
    ScreenDef(
        route="/catalogo",
        label="Catálogo",
        icon="INVENTORY_2",
        permission="com.catalogo.ver",
        group=_GRUPO_CATALOGO,
        order=1,
    ),
    ScreenDef(
        route="/catalogo/importar",
        label="Importar catálogo",
        icon="UPLOAD_FILE",
        permission="com.catalogo.importar",
        group=_GRUPO_CATALOGO,
        order=2,
    ),
    ScreenDef(
        route="/inventario",
        label="Inventario",
        icon="WAREHOUSE",
        permission="com.inventario.ver",
        group=_GRUPO_INVENTARIO,
        order=1,
    ),
    ScreenDef(
        route="/inventario/stock-bajo",
        label="Stock bajo",
        icon="PRIORITY_HIGH",
        permission="com.inventario.ver",
        group=_GRUPO_INVENTARIO,
        order=2,
    ),
    ScreenDef(
        route="/contrapartes",
        label="Contrapartes",
        icon="CONTACTS",
        permission="com.contrapartes.ver",
        group=_GRUPO_COMPRAS,
        order=1,
    ),
    ScreenDef(
        route="/compras",
        label="Compras",
        icon="SHOPPING_CART",
        permission="com.compras.ver",
        group=_GRUPO_COMPRAS,
        order=2,
    ),
    ScreenDef(
        route="/compras/nueva",
        label="Nueva compra",
        icon="ADD_SHOPPING_CART",
        permission="com.compras.registrar",
        group=_GRUPO_COMPRAS,
        order=3,
    ),
    ScreenDef(
        route="/cxp",
        label="Cuentas por pagar",
        icon="RECEIPT_LONG",
        permission="com.cxp.ver",
        group=_GRUPO_COMPRAS,
        order=4,
    ),
)

COMERCIAL_MODULE = ModuleDef(
    code="comercial",
    label="Comercial",
    permissions=_PERMISOS,
    profiles=(_PERFIL_VENDEDOR, _PERFIL_BODEGA, _PERFIL_GERENTE),
    screens=_PANTALLAS,
)
