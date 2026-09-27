"""Pruebas de ModuleRegistry: unicidad de códigos y validación diferida de perfiles."""

import pytest

from sistemashn.core.modules.contracts import (
    ModuleDef,
    ModuleRegistry,
    PermissionDef,
    ProfileDef,
    ScreenDef,
)


def _modulo(
    code: str,
    permisos: tuple[PermissionDef, ...] = (),
    perfiles: tuple[ProfileDef, ...] = (),
    pantallas: tuple[ScreenDef, ...] = (),
) -> ModuleDef:
    return ModuleDef(
        code=code, label=code, permissions=permisos, profiles=perfiles, screens=pantallas
    )


def test_registra_permisos_perfiles_y_pantallas() -> None:
    registry = ModuleRegistry()
    permiso = PermissionDef("core.usuarios.ver", "Ver usuarios", "Administración")
    perfil = ProfileDef("administrador", "Administrador", frozenset({permiso.code}))
    pantalla = ScreenDef("/usuarios", "Usuarios", "PEOPLE", permiso.code, "Administración", 1)
    registry.register(_modulo("core", (permiso,), (perfil,), (pantalla,)))

    assert registry.module_codes() == frozenset({"core"})
    assert registry.permissions() == {permiso.code: permiso}
    assert registry.profiles() == {perfil.code: perfil}
    assert registry.screens() == [pantalla]


def test_modulo_duplicado_falla() -> None:
    registry = ModuleRegistry()
    registry.register(_modulo("core"))
    with pytest.raises(ValueError, match="módulo duplicado"):
        registry.register(_modulo("core"))


def test_permiso_duplicado_entre_modulos_falla() -> None:
    registry = ModuleRegistry()
    permiso = PermissionDef("core.usuarios.ver", "Ver usuarios", "Administración")
    registry.register(_modulo("core", (permiso,)))
    with pytest.raises(ValueError, match="permiso duplicado"):
        registry.register(_modulo("otro", (permiso,)))


def test_perfil_duplicado_falla() -> None:
    registry = ModuleRegistry()
    perfil = ProfileDef("administrador", "Administrador", frozenset())
    registry.register(_modulo("core", perfiles=(perfil,)))
    with pytest.raises(ValueError, match="perfil duplicado"):
        registry.register(_modulo("otro", perfiles=(perfil,)))


def test_ruta_duplicada_falla() -> None:
    registry = ModuleRegistry()
    pantalla = ScreenDef("/usuarios", "Usuarios", "PEOPLE", None, "Administración", 1)
    registry.register(_modulo("core", pantallas=(pantalla,)))
    with pytest.raises(ValueError, match="pantalla duplicado"):
        registry.register(_modulo("otro", pantallas=(pantalla,)))


def test_perfil_con_permiso_inexistente_falla_al_consultar_profiles() -> None:
    # La validación es diferida: los módulos se registran en orden arbitrario y un permiso
    # referenciado puede llegar en un registro posterior (o nunca).
    registry = ModuleRegistry()
    perfil = ProfileDef("vendedor", "Vendedor", frozenset({"comercial.ventas.crear"}))
    registry.register(_modulo("comercial", perfiles=(perfil,)))

    with pytest.raises(ValueError, match="permisos inexistentes"):
        registry.profiles()


def test_validate_corre_todas_las_validaciones() -> None:
    registry = ModuleRegistry()
    perfil = ProfileDef("vendedor", "Vendedor", frozenset({"comercial.ventas.crear"}))
    registry.register(_modulo("comercial", perfiles=(perfil,)))

    with pytest.raises(ValueError, match="permisos inexistentes"):
        registry.validate()


def test_perfil_valido_si_permiso_llega_en_modulo_posterior() -> None:
    registry = ModuleRegistry()
    perfil = ProfileDef("vendedor", "Vendedor", frozenset({"comercial.ventas.crear"}))
    registry.register(_modulo("comercial", perfiles=(perfil,)))
    permiso = PermissionDef("comercial.ventas.crear", "Crear venta", "Ventas")
    registry.register(_modulo("comercial_permisos", (permiso,)))

    assert registry.profiles() == {perfil.code: perfil}
