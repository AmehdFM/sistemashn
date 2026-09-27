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
| T3.2 Compras | Hecha | `comercial/compras/`, migración `0002_compras.py`, 14 pruebas (contado, crédito, pagos mixtos, fallo en última línea no deja rastro, idempotencia, historial de precios) |
| T3.3 Cuentas por pagar/cobrar | Hecha (revisada: `AccountService` estaba implementado y probado pero no se registraba en `composition.py`; ya corregido) | `tests/comercial/credito/` |
| T3.4 Pantallas | Hecha | `contrapartes_view.py`, `compras_view.py` (historial + nueva compra), `cxp_view.py`, registradas en `comercial/ui/screens.py` |

## Fase 4 — Cotizaciones, POS, pagos, caja y cuentas por cobrar

| Tarea | Estado | Evidencia |
|---|---|---|
| T4.1 Cotizaciones y apartados | Hecha | `comercial/cotizaciones/`, vencimiento perezoso, reserva de kits componente a componente, 13 pruebas |
| T4.2 Ventas y comprobante interno | Hecha | `comercial/ventas/`, expansión de kits con snapshot de costo, conversión de cotización con `QuoteConversionMismatch`, 11 pruebas |
| T4.3 Caja | Hecha | `comercial/caja/`, movimientos append-only, apertura/cierre con conciliación, 20 pruebas |
| T4.4 Cuentas por cobrar | Hecha (sin código nuevo: reutiliza `AccountService` con `AccountKind.RECEIVABLE`) | integración probada en `tests/comercial/ventas/` |
| T4.5 Factura legal (CAI) | Hecha, deshabilitada por defecto | `comercial/fiscal/`, nunca emite fuera de rango/vigencia, 8 pruebas |
| T4.6 Pantallas | Hecha | `pos_view.py`, `cotizaciones_view.py`, `ventas_view.py`, `caja_view.py`, `cxc_view.py`, registradas en `comercial/ui/screens.py` |

## Fase 5 — Anulaciones, devoluciones, documentos y reportes

| Tarea | Estado | Evidencia |
|---|---|---|
| T5.1 Anulaciones | Hecha | `InventoryLedger.void_reversal_of_receive/_of_issue`, `SaleService.void`, `PurchaseService.void`, `AccountService.void`, `CashService.reverse_entry`; 10 pruebas nuevas |
| T5.2/T5.3 Devoluciones de cliente y proveedor | Hecha | `comercial/devoluciones/`, saldo a favor vía `com_account(kind='credit_note')`, 20 pruebas |
| T5.4 Documentos PDF | Hecha | `core/documents/renderer.py` (promovido de la sonda de Etapa 0), `comercial/documentos/`, 24 pruebas |
| T5.5 Excel y reportes | Hecha | `comercial/reportes/`, utilidad con costo histórico, exporta a Excel, 14 pruebas |
| T5.6 Pantallas | Hecha | `devoluciones_view.py`, `reportes_view.py`, registradas en `comercial/ui/screens.py` |
