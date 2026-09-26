# ADR 001: toolchain de la sonda de etapa 0

Estado: provisional hasta la prueba en Windows.

El Codespace usa CPython 3.14.2 x64. El proyecto declara `>=3.14,<3.15` y
`uv.lock` fija las versiones resueltas. Se instala con
`UV_LINK_MODE=copy python -m uv sync --extra dev` y se prueba con
`UV_LINK_MODE=copy python -m uv run --extra dev pytest`. La sonda arranca con
`python -m uv run python -m sistemashn.probe` en un entorno con pantalla.
El Codespace resolvió Flet 1.0.1, SQLAlchemy 2.1.1, Alembic 1.20.0 y
pytest 9.1.1 el 26 de septiembre de 2026; el lock conserva sus hashes y
dependencias transitivas. `uv` 0.12.19 se instaló en el Codespace con
`python -m pip install --user uv`; el ejecutable no está en su `PATH`.

Flet 1.x es la línea de API elegida: `ft.run(main)`, `ft.Button` y cambios de
estado en el manejador de eventos. `flet build windows` es el candidato para
empaquetar, pendiente de la tarea 4 y de comprobar el comando y Flutter en
Windows real. El paquete de datos se configura con `SISTEMASHN_DATA_DIR`; en
Windows, por defecto, usa `%LOCALAPPDATA%/SistemasHN`. Nunca se escribe en la
carpeta del ejecutable.

Pydantic, openpyxl, argon2-cffi y cryptography se incorporan en sus etapas
funcionales; no forman parte de esta sonda. PDF, impresión y empaquetado final
siguen pendientes de verificación. Registrar aquí versiones reales del lock,
comando y hash/tamaño de artefacto cuando se construya en Windows.
