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
.\sistemashn.ps1       # menú: ejecutar, compilar o generar licencia; luego elegir vertical
.\sistemashn.ps1 run -Vertical repuestos
.\sistemashn.ps1 run -Vertical ferreteria
.\scripts\dev.ps1 test   # pytest completo, ruff check y formato
.\scripts\dev.ps1 build -Vertical repuestos  # pruebas + ejecutable Windows y ZIP
.\scripts\dev.ps1 run -Vertical ferreteria   # datos aislados en .dev-data/manual-ferreteria
```

También se puede abrir `SistemasHN.cmd` con doble clic: deja la consola abierta al terminar.
El menú muestra solo verticales cuyo punto de entrada esté disponible. Cada vertical usa su
propia carpeta de datos; la licencia de desarrollo se genera para la vertical elegida.
El flujo y los límites de Ferretería están en [docs/ferreteria.md](docs/ferreteria.md).

`build` incluye las migraciones fuente que Alembic necesita y arranca el ejecutable con una
base temporal para comprobar que crea `core_installation`. El resultado queda en
`build/windows_release/` y `build/SistemasHNRepuestos<version>.zip` para Repuestos; en
`build/windows_release_ferreteria/` y `build/SistemasHNFerreteria<version>.zip` para Ferretería.
