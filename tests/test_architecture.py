"""Verifica las reglas de dependencia entre capas (spec §2)."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "sistemashn"

FORBIDDEN = {
    "core": ("sistemashn.comercial", "sistemashn.repuestos", "sistemashn.app"),
    "comercial": ("sistemashn.repuestos", "sistemashn.app"),
    "repuestos": ("sistemashn.app",),
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_layer_dependencies() -> None:
    violations = []
    for layer, forbidden in FORBIDDEN.items():
        for file in (SRC / layer).rglob("*.py"):
            for name in _imports(file):
                if name.startswith(forbidden):
                    violations.append(f"{file.relative_to(SRC)} importa {name}")
    assert violations == []
