"""Completa el primer arranque de una base de desarrollo (solo pruebas locales).

Firma la licencia con la clave de desarrollo del vendedor (`tools/vendor/keys/dev-2026.priv`)
y deja un administrador `admin` con la contraseña indicada. Imprime los códigos de recuperación.

Uso: evn/Scripts/python.exe scripts/dev_setup_demo.py [data_dir] [contraseña]
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sistemashn.app.bootstrap import build_context  # noqa: E402
from sistemashn.core.settings.schemas import BusinessInput  # noqa: E402
from sistemashn.core.setup.service import SetupStep  # noqa: E402


def main() -> None:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".dev-data"
    password = sys.argv[2] if len(sys.argv) > 2 else "Demo-2026!"
    ctx = build_context(data_dir)
    setup = ctx.service("setup")
    state = setup.state()
    if state.step == SetupStep.LICENSE:
        signed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "vendor" / "vendedor.py"),
                "sign-license",
                "--request",
                state.request_code,
                "--business",
                "Repuestos Demo",
                "--key",
                str(ROOT / "tools" / "vendor" / "keys" / "dev-2026.priv"),
                "--key-id",
                "dev-2026",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        setup.submit_license(signed)
        state = setup.state()
    if state.step == SetupStep.BUSINESS:
        setup.submit_business(
            BusinessInput(
                name="Repuestos Demo",
                legal_name="Repuestos Demo S. de R.L.",
                address="Tegucigalpa",
                phone="2222-0000",
                email="demo@example.com",
            ),
            None,
        )
        state = setup.state()
    if state.step == SetupStep.ADMIN:
        codes = setup.create_admin("admin", "Administrador", password)
        print("Códigos de recuperación:", ", ".join(codes))
        state = setup.state()
    if state.step == SetupStep.RECOVERY:
        setup.confirm_recovery_codes_saved()
    print("Configuración:", setup.state().step)


if __name__ == "__main__":
    main()
