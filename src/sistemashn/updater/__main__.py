"""Entrada de línea de comandos del proceso `updater` (empaquetado aparte, T6.3).

Uso: `updater package installation db_path work_dir lock_file`. No relanza la app
automáticamente al terminar (decisión de la fase para v1: más simple y predecible);
solo muestra el resultado e instruye al usuario a abrir la app manualmente.
"""

import argparse
import sys
from pathlib import Path

from sistemashn.updater.runner import run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="updater", description="Aplica un paquete de actualización firmado de SistemasHN"
    )
    parser.add_argument("package", type=Path, help="ruta al ZIP de actualización ya validado")
    parser.add_argument("installation", type=Path, help="carpeta de instalación del programa")
    parser.add_argument("db_path", type=Path, help="ruta al archivo de base de datos")
    parser.add_argument("work_dir", type=Path, help="carpeta de trabajo para staging/rollback")
    parser.add_argument("lock_file", type=Path, help="archivo de bloqueo de la app (.app.lock)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    resultado = run_update(
        args.package, args.installation, args.db_path, args.work_dir, args.lock_file
    )

    if resultado.ok:
        print(f"Actualización aplicada: {resultado.from_version} -> {resultado.to_version}")
        print("Actualización completa. Abra SistemasHN manualmente.")
        return 0

    print(f"Actualización fallida ({resultado.from_version} -> {resultado.to_version}):")
    print(f"  error: {resultado.error}")
    print(f"  revertido: {'sí' if resultado.rolled_back else 'no'}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
