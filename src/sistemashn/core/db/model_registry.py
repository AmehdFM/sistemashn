"""Importa todos los módulos de modelos para que queden registrados en `Base.metadata`."""

import importlib
import pkgutil


def import_all_models() -> None:
    import sistemashn

    for info in pkgutil.walk_packages(sistemashn.__path__, "sistemashn."):
        if info.name.endswith(".models"):
            importlib.import_module(info.name)
