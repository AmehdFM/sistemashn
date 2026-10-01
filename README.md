# SistemasHN

POS/ERP offline para negocios de repuestos en Honduras, hecho con Python 3.14, Flet 1.0,
SQLAlchemy 2 (SQLite) y Alembic. Corre local, sin dependencia de internet, en equipos Windows
de un negocio. La primera entrega instalable es el vertical de Repuestos; Ferretería y Clínica
son extensiones futuras planeadas pero no bloquean esta entrega.

Documentación completa del diseño, planes y estado de avance en [`docs/README.md`](docs/README.md).
¿No encuentras algo en el repositorio? Empieza por
[`docs/mapa-del-proyecto.md`](docs/mapa-del-proyecto.md): dónde compilar, dónde están las
pruebas, y qué hace cada carpeta de `src/`.

## Requisitos

- Python 3.14 (CPython) instalado en el sistema.
- Entorno virtual propio del proyecto, llamado `evn`, dentro de la raíz del repositorio.
- Nada se instala fuera de `evn` (ver `docs/decisions/001-toolchain.md`).

## Instalación

```bat
py -3.14 -m venv evn
evn\Scripts\python.exe -m pip install -r requirements-dev.txt
evn\Scripts\python.exe -m pip install -e . --no-deps
```

## Correr la app

```bat
evn\Scripts\python.exe src\main.py
```

El motor resuelve la carpeta de datos con, en orden de prioridad: el argumento `--data-dir`,
la variable de entorno `SISTEMASHN_DATA_DIR`, o una carpeta por defecto. Por ejemplo, para usar
datos de prueba:

```bat
evn\Scripts\python.exe src\main.py --data-dir .dev-data\manual
```

## Probar y compilar en Windows

Desde PowerShell, en la raíz del repositorio:

```powershell
.\scripts\dev.ps1 test   # pytest completo, ruff check y formato
.\scripts\dev.ps1 build  # lo anterior + ejecutable Windows y ZIP en build/
.\scripts\dev.ps1 run    # app de escritorio con datos aislados en .dev-data/manual
```

`build` incluye las migraciones fuente que Alembic necesita y arranca el ejecutable con una
base temporal para comprobar que crea `core_installation`. El resultado queda en
`build/windows_release/` y `build/SistemasHNRepuestos<version>.zip`.
