# ADR-001: herramientas y entorno

Fecha: 2026-09-26 · Estado: aceptada

- Intérprete: CPython 3.14.3 x64 en el venv del proyecto `evn\` (pip). Nada se instala fuera de `evn`.
- Dependencias de ejecución fijadas en `pyproject.toml` y `requirements.txt`; de desarrollo en `requirements-dev.txt`.
  flet 1.0.0, SQLAlchemy 2.0.54, alembic 1.20.0, pydantic 2.13.5, openpyxl 3.1.5, argon2-cffi 25.1.0,
  cryptography 50.0.1, fpdf2 2.8.8, httpx 0.28.1; dev: pytest 9.1.1, ruff 0.16.8, pyinstaller 6.22.3, flet-cli/desktop 1.0.0.
- Instalación: `evn\Scripts\python.exe -m pip install -r requirements-dev.txt` y `evn\Scripts\python.exe -m pip install -e . --no-deps`.
- Calidad: `evn\Scripts\python.exe -m pytest -q`, `... -m ruff check src tests tools`, `... -m ruff format`.
- Entrada Flet: `src/main.py` (delgada) → `sistemashn.app.repuestos.main`.
- Empaquetado: `flet build windows` (requiere Flutter SDK y Visual Studio 2022 con C++; presentes en la PC de desarrollo),
  PyInstaller onefile para `updater.exe`, Inno Setup para el instalador. Resultados en `docs/validation/stage-0-windows.md`.
- PDF: fpdf2 (Python puro) con fuente TTF incluida para caracteres españoles; impresión por `os.startfile(ruta, "print")`.
