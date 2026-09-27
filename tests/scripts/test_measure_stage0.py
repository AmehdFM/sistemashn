"""Prueba de guarda del script de medición (T0.5b): ExePath inexistente -> exit 2."""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "measure_stage0.ps1"


@pytest.mark.skipif(sys.platform != "win32", reason="script de PowerShell solo en Windows")
def test_exepath_inexistente_sale_con_codigo_2(tmp_path: Path) -> None:
    exe_inexistente = tmp_path / "no-existe.exe"
    out_dir = tmp_path / "salida"

    resultado = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-ExePath",
            str(exe_inexistente),
            "-OutDir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert resultado.returncode == 2
    assert not (out_dir / "stage0-measurements.json").exists()
