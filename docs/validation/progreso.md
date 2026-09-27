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
| T2.6 Pantallas | En curso | Falta registrar `units_categories_view.py` (existe pero no tiene ruta en `comercial/module.py` ni en `comercial/ui/screens.py`) y falta la pantalla de kits (`/kits`, sin builder ni ruta). El resto del plan (catálogo, importación, inventario, stock bajo, vehículos, compatibles) sí está implementado y registrado. |

## Fase 3 — Compras y crédito

| Tarea | Estado | Evidencia |
|---|---|---|
| T3.1 Contrapartes, idempotencia, numeración, métodos de pago | Hecha | |
| T3.2 Compras | Pendiente | |
| T3.3 Cuentas por pagar/cobrar | En curso | |
| T3.4 Pantallas | Pendiente | |
