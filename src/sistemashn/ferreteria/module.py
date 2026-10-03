"""Permisos y navegación de Ferretería."""

from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.modules.contracts import ModuleDef, PermissionDef, ProfileDef, ScreenDef

_GROUP = "Ferretería"

FERRETERIA_MODULE = ModuleDef(
    code="ferreteria",
    label="Ferretería",
    permissions=(
        PermissionDef(
            "fer.catalogo.gestionar", "Gestionar datos técnicos y presentaciones", _GROUP
        ),
    ),
    profiles=(
        ProfileDef(
            code="ferreteria_gerente",
            label="Gerente de ferretería",
            permissions=frozenset(
                {permission.code for permission in COMERCIAL_MODULE.permissions}
                | {"fer.catalogo.gestionar"}
            ),
        ),
        ProfileDef(
            code="ferreteria_bodega",
            label="Bodega de ferretería",
            permissions=frozenset(
                {
                    "com.catalogo.ver",
                    "com.catalogo.gestionar",
                    "com.catalogo.importar",
                    "com.inventario.ver",
                    "com.inventario.ajustar",
                    "com.contrapartes.ver",
                    "com.compras.ver",
                    "com.compras.registrar",
                    "fer.catalogo.gestionar",
                }
            ),
        ),
    ),
    screens=(
        ScreenDef(
            route="/ferreteria/resumen",
            label="Resumen del negocio",
            icon="INSIGHTS",
            permission="com.reportes.ver",
            group=_GROUP,
            order=1,
        ),
        ScreenDef(
            route="/ferreteria/presentaciones",
            label="Medidas y empaques",
            icon="STRAIGHTEN",
            permission="com.catalogo.ver",
            group=_GROUP,
            order=2,
        ),
    ),
)
