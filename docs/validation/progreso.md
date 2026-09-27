# Progreso de desarrollo v1

Plan de dirección: fases 0–6 (ver `docs/superpowers/plans/2026-09-25-plan-general.md`). Un commit por fase en `desarrollo`.

| Tarea | Estado | Evidencia |
|---|---|---|
| T0.1 Higiene, pyproject, requirements, esqueleto, prueba de arquitectura, ADR-001/002 | Hecha | `pytest` 1 passed, ruff limpio |
| T0.2 core/db, tipos exactos, UoW, Alembic sonda | Hecha (revisada: se añadió BEGIN IMMEDIATE para escrituras) | 49 passed |
| T0.3 Respaldo y restauración | Hecha (revisada: limpieza de .partial en restore) | 14 pruebas |
| T0.4 Actualización de ensayo ZIP con reversión | Hecha | 17 pruebas, ADR-003 |
| T0.5a Build `flet build windows` + medición | Hecha | `docs/validation/stage-0-windows.md` (147 MB, ventana 0.65 s) |
| T0.5b PDF fpdf2 (80 mm/carta) e impresión, script de medición | Hecha | `docs/validation/muestras/` |
| T0.5c PyInstaller updater e Inno Setup | Pendiente | |

## Fase 1 — Core

| Tarea | Estado | Evidencia |
|---|---|---|
| T1.1 Módulos y autorización (+ modelo User) | Hecha (revisada: corregida escalada por perfil y rol admin leído de la base; auditoría conectada) | |
| T1.2 Identidad | Hecha (revisada: verificación señuelo contra enumeración de usuarios) | |
| T1.3 Auditoría | Hecha (append-only por triggers) | |
| T1.4 Licencia offline | Hecha (revisada: la firma cubre el prefijo; clave dev `dev-2026`) | |
| T1.5 Ajustes y primer arranque | Hecha | |
| T1.6a UI base (tema, router, widgets, shell) | Hecha | |
| T1.6b Pantallas Core y composición de la app | Hecha | Verificado en navegador: login, usuarios, auditoría; primer arranque con licencia firmada por `vendedor.py` (`scripts/dev_setup_demo.py`) |

Transversal: tipo `UtcDateTime` (fechas siempre UTC aware) añadido tras detectar pérdida de zona horaria en SQLite.

## Fase 2 — Catálogo, inventario y Repuestos

| Tarea | Estado | Evidencia |
|---|---|---|
| T2.1 Catálogo + módulo comercial | Hecha (revisada: escape de LIKE) | |
| T2.2 Libro de inventario | Hecha | promedio ponderado verificado |
| T2.3 Kits | Hecha | salida atómica de componentes |
| T2.4 Repuestos (partes, equivalencias, vehículos) | Hecha | |
| T2.5 Excel | Hecha | 1,000 filas < 10 s |
| T2.6 Pantallas | Hecha (revisada: la nota anterior de "falta registrar" era incorrecta) | `units_categories_view.py` sí está en uso: `catalog_view.py` abre sus diálogos de Unidades/Categorías desde la pantalla `/catalogo`. La composición de kits no es una ruta aparte sino una sección embebida en el formulario de producto (`_kit_section` en `catalog_view.py`, visible cuando `is_kit=True`), consistente con que un kit es un producto más del catálogo. Repuestos agrega su pestaña de parte/equivalencias vía el hook `ProductFormExtension` (`repuestos/ui/part_extension.py`) y sus pantallas de vehículos/compatibles (`/repuestos/vehiculos`, `/repuestos/compatibles`) registradas en `repuestos/ui/screens.py`. Todo cubierto por pruebas existentes. |

## Fase A — Cierre de deuda técnica y script de pruebas

| Tarea | Estado | Evidencia |
|---|---|---|
| Script `scripts\pruebas.bat` (11 opciones, CRLF, `.gitattributes`) | Hecha | |
| Cadena real de migraciones Alembic (`0001_base.py`, retiro de `create_all` en bootstrap) | Hecha | `tests/core/db/test_schema_matches_models.py`: `compare_metadata` vacío + triggers append-only verificados |
| Documentación (`docs/README.md`, `README.md`, evidencia T2.6) | Hecha | |

## Fase 3 — Compras y crédito

| Tarea | Estado | Evidencia |
|---|---|---|
| T3.1 Contrapartes, idempotencia, numeración, métodos de pago | Hecha | |
| T3.2 Compras | Pendiente | |
| T3.3 Cuentas por pagar/cobrar | En curso | |
| T3.4 Pantallas | Pendiente | |
