"""Pruebas del registro de `COMERCIAL_MODULE` junto con `CORE_MODULE`."""

from sistemashn.comercial.catalogo.search import normalize_search
from sistemashn.comercial.module import COMERCIAL_MODULE
from sistemashn.core.modules.contracts import ModuleRegistry
from sistemashn.core.modules.core_module import CORE_MODULE


def test_comercial_module_se_registra_junto_a_core() -> None:
    registry = ModuleRegistry()
    registry.register(CORE_MODULE)
    registry.register(COMERCIAL_MODULE)
    registry.validate()

    permisos = registry.permissions()
    assert "com.catalogo.ver" in permisos
    assert "com.inventario.ajustar" in permisos

    perfiles = registry.profiles()
    assert perfiles["vendedor"].permissions == frozenset(
        {"com.catalogo.ver", "com.inventario.ver", "com.cxc.ver"}
    )

    rutas = {s.route for s in registry.screens()}
    assert {"/catalogo", "/inventario", "/inventario/stock-bajo", "/catalogo/importar"} <= rutas


def test_normalize_search_quita_acentos_y_minusculas() -> None:
    assert normalize_search("Pastillas Freón") == "pastillas freon"
    assert normalize_search("  CÓDIGO  ") == "codigo"
