"""Ejecuta la app en modo web local (solo desarrollo/pruebas de UI en navegador).

Uso: evn/Scripts/python.exe scripts/run_web_dev.py [puerto]
Los datos van a SISTEMASHN_DATA_DIR (por defecto .dev-data/ en el repo, ignorado por git).
"""

import os
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("SISTEMASHN_DATA_DIR", str(ROOT / ".dev-data"))
os.environ["FLET_FORCE_WEB_SERVER"] = "true"  # servidor web sin abrir el navegador del sistema
sys.path.insert(0, str(ROOT / "src"))

from sistemashn.app.repuestos import main  # noqa: E402

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8551
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=port, host="127.0.0.1")
