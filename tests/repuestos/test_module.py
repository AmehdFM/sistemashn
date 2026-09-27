"""Pruebas del `ModuleDef` de Repuestos (T2.4)."""

from sistemashn.repuestos.module import REPUESTOS_MODULE


def test_repuestos_module_registrable(registry):
    # `registry` ya registra CORE, COMERCIAL y REPUESTOS: validar consistencia.
    registry.validate()
    codigos = {p.code for p in REPUESTOS_MODULE.permissions}
    assert codigos == {"rep.partes.gestionar", "rep.vehiculos.gestionar"}


def test_perfil_repuestos_bodega_extiende_bodega_comercial(registry):
    perfiles = registry.profiles()
    perfil = perfiles["repuestos_bodega"]
    assert "rep.partes.gestionar" in perfil.permissions
    assert "com.inventario.ajustar" in perfil.permissions


def test_pantallas_repuestos_registradas(registry):
    rutas = {s.route for s in registry.screens()}
    assert "/repuestos/vehiculos" in rutas
    assert "/repuestos/compatibles" in rutas
