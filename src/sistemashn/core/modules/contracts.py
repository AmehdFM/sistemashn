"""Contratos de registro de módulos: permisos, perfiles y pantallas (spec §5, T1.1)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PermissionDef:
    code: str
    label: str
    group: str
    sensitive: bool = False


@dataclass(frozen=True)
class ProfileDef:
    code: str
    label: str
    permissions: frozenset[str]
    #: Ruta inicial de este perfil al entrar al sistema (T7.6); si es None, se usa la
    #: primera pantalla visible, como hasta ahora.
    home_route: str | None = None
    #: Arranca en "modo mostrador" (sin barra lateral, T7.5) salvo que el usuario cambie
    #: a "Menú completo" desde la pantalla.
    simplified_by_default: bool = False


@dataclass(frozen=True)
class ScreenDef:
    route: str
    label: str
    icon: str
    permission: str | None
    group: str
    order: int
    #: Pantallas de uso poco frecuente (T7.6): se agrupan en "Configuración avanzada" al
    #: final de la barra lateral en vez de mezclarse con el uso diario.
    advanced: bool = False


@dataclass(frozen=True)
class ModuleDef:
    code: str
    label: str
    permissions: tuple[PermissionDef, ...] = field(default_factory=tuple)
    profiles: tuple[ProfileDef, ...] = field(default_factory=tuple)
    screens: tuple[ScreenDef, ...] = field(default_factory=tuple)


class ModuleRegistry:
    """Registro central de módulos: valida unicidad de códigos y consistencia perfil/permiso."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleDef] = {}

    def register(self, module: ModuleDef) -> None:
        if module.code in self._modules:
            raise ValueError(f"módulo duplicado: {module.code}")

        permisos_existentes = {p.code for m in self._modules.values() for p in m.permissions}
        self._check_duplicados("permiso", (p.code for p in module.permissions), permisos_existentes)

        perfiles_existentes = {p.code for m in self._modules.values() for p in m.profiles}
        self._check_duplicados("perfil", (p.code for p in module.profiles), perfiles_existentes)

        rutas_existentes = {s.route for m in self._modules.values() for s in m.screens}
        self._check_duplicados("pantalla", (s.route for s in module.screens), rutas_existentes)

        self._modules[module.code] = module

    def _check_duplicados(self, nombre: str, nuevos, existentes: set[str]) -> None:
        vistos = set(existentes)
        for codigo in nuevos:
            if codigo in vistos:
                raise ValueError(f"{nombre} duplicado: {codigo}")
            vistos.add(codigo)

    def permissions(self) -> dict[str, PermissionDef]:
        resultado: dict[str, PermissionDef] = {}
        for module in self._modules.values():
            for permiso in module.permissions:
                resultado[permiso.code] = permiso
        return resultado

    def profiles(self) -> dict[str, ProfileDef]:
        permisos_conocidos = self.permissions()
        resultado: dict[str, ProfileDef] = {}
        for module in self._modules.values():
            for perfil in module.profiles:
                faltantes = perfil.permissions - permisos_conocidos.keys()
                if faltantes:
                    raise ValueError(
                        f"perfil '{perfil.code}' referencia permisos inexistentes: "
                        f"{sorted(faltantes)}"
                    )
                resultado[perfil.code] = perfil
        return resultado

    def screens(self) -> list[ScreenDef]:
        todas = [screen for module in self._modules.values() for screen in module.screens]
        return sorted(todas, key=lambda s: (s.group, s.order))

    def module_codes(self) -> frozenset[str]:
        return frozenset(self._modules.keys())

    def validate(self) -> None:
        """Corre todas las validaciones diferidas (perfiles con permisos inexistentes)."""
        self.permissions()
        self.profiles()
        self.screens()
