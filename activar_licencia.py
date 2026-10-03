"""Genera y firma una licencia de desarrollo para pasar el primer arranque en local.

Solo para desarrollo/pruebas: usa una clave "dev-2026" generada en este mismo equipo
(`tools/vendor/keys/`, fuera de git). Si no existe, la crea con `vendedor.py keygen` y
sincroniza la clave publica en `src/sistemashn/core/licensing/keys.py` para que la app
la reconozca (la clave publica que ya estaba en ese archivo no tiene una privada
disponible en este repositorio, por eso hace falta generar una nueva).

Uso:
    evn\\Scripts\\python.exe activar_licencia.py [--data-dir RUTA] [--vertical VERTICAL]
        [--business "Nombre"]

Imprime el codigo de activacion (SHN1...) para pegarlo en la pantalla de primer
arranque de la app.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

KEY_ID = "dev-2026"
KEYS_DIR = ROOT / "tools" / "vendor" / "keys"
PRIV_PATH = KEYS_DIR / f"{KEY_ID}.priv"
PUB_PATH = KEYS_DIR / f"{KEY_ID}.pub.txt"
VENDEDOR = ROOT / "tools" / "vendor" / "vendedor.py"
KEYS_MODULE = ROOT / "src" / "sistemashn" / "core" / "licensing" / "keys.py"


def _ensure_dev_key() -> None:
    """Genera la clave `dev-2026` si falta y sincroniza su clave publica en `keys.py`."""
    if not PRIV_PATH.exists():
        print(f"No existe {PRIV_PATH}; generando clave de desarrollo nueva...")
        resultado = subprocess.run(
            [
                sys.executable,
                str(VENDEDOR),
                "keygen",
                "--out",
                str(KEYS_DIR),
                "--key-id",
                KEY_ID,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(resultado.stdout.strip())

    clave_publica = PUB_PATH.read_text(encoding="utf-8").strip()
    contenido = KEYS_MODULE.read_text(encoding="utf-8")
    if clave_publica not in contenido:
        nuevo_contenido = re.sub(
            r'"dev-2026": b64url_decode\("[^"]+"\)',
            f'"dev-2026": b64url_decode("{clave_publica}")',
            contenido,
        )
        if nuevo_contenido == contenido:
            raise SystemExit(
                f"No se pudo actualizar {KEYS_MODULE} automaticamente. Copie a mano la "
                f'clave publica en VENDOR_PUBLIC_KEYS["dev-2026"]: {clave_publica}'
            )
        KEYS_MODULE.write_text(nuevo_contenido, encoding="utf-8")
        print(f"Actualizado {KEYS_MODULE} con la clave publica de desarrollo local.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Carpeta de datos de la instalacion a activar",
    )
    parser.add_argument(
        "--business",
        default=None,
        help="Nombre de negocio que queda grabado en la licencia (solo informativo)",
    )
    parser.add_argument(
        "--vertical",
        choices=("repuestos", "ferreteria"),
        default="repuestos",
        help="Vertical de la instalación que se va a activar",
    )
    args = parser.parse_args()
    data_path = (
        Path(args.data_dir)
        if args.data_dir
        else (
            ROOT / ".dev-data" / ("manual" if args.vertical == "repuestos" else "manual-ferreteria")
        )
    )

    _ensure_dev_key()

    from sistemashn.app.bootstrap import build_context
    from sistemashn.core.setup.service import SetupStep

    contexto = build_context(data_path, vertical=args.vertical)
    setup = contexto.service("setup")
    estado = setup.state()

    if estado.step != SetupStep.LICENSE:
        print(f"Esta instalacion ya paso el paso de licencia (paso actual: {estado.step.value}).")
        return

    print()
    print(f"Codigo de solicitud: {estado.request_code}")

    codigo_activacion = subprocess.run(
        [
            sys.executable,
            str(VENDEDOR),
            "sign-license",
            "--request",
            estado.request_code,
            "--business",
            args.business or f"{args.vertical.capitalize()} Demo",
            "--key",
            str(PRIV_PATH),
            "--key-id",
            KEY_ID,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    print()
    print("Codigo de activacion (peguelo en la pantalla de primer arranque):")
    print(codigo_activacion)
    print()


if __name__ == "__main__":
    main()
