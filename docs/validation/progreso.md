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

## Fase 7 — Mejoras de UI/UX (fuera de la numeración original, investigación + plan del dueño)

| Tarea | Estado | Evidencia |
|---|---|---|
| T7.1 Permisos `com.ventas.credito`/`com.ventas.descuento` | Hecha | `comercial/module.py`, solo perfil `gerente` por defecto |
| T7.2 `core_business`: columnas de operación nuevas | Hecha | migración `0005_operacion_ui.py`, `OperationSettingsInput`/`update_operation_settings` |
| T7.3 Comportamientos condicionados a `core_business` | Hecha | `SaleService.confirm` (caja/backorder/crédito/descuento), `AccountService.pay`, devolución "sin comprobante" |
| T7.4 Fotos de producto | Hecha | `com_product.image_path`, `CatalogService.set_image`, miniatura en catálogo |
| T7.5 POS: modo mostrador, ventas en espera, confirmación con resumen | Hecha (equivalencias sin stock, prioridad 4, quedó pendiente) | `ParkedSalesStore`, `pos_view.py` |
| T7.6 Pantalla "Ajustes de operación" y "Configuración avanzada" | Hecha | `operation_settings_view.py`, `ScreenDef.advanced`, `ProfileDef.home_route` |

## Fase 6 — Operación y entrega

Planificada desde el inicio del proyecto pero no se había codificado hasta esta ronda (el
placeholder de Respaldos quedó pendiente desde la Fase 1). Implementada íntegramente ahora,
después de la Fase 7, a pedido del dueño tras un repaso de brechas para una v1 vendible.

| Tarea | Estado | Evidencia |
|---|---|---|
| T6.1 Pantalla de respaldos real | Hecha | `BackupService` (`core/operations/service.py`), `backups_view.py`, historial y recordatorio vía `core_setting` (sin tabla nueva) |
| T6.2 Paquete de actualización firmado | Hecha | `core/updater/keys.py` (clave `update-2026`), `core/updater/package.py`, `vendedor.py sign-update` |
| T6.3 Proceso `updater/` | Hecha | `src/sistemashn/updater/` (`runner.py`, `__main__.py`), `src/updater_main.py`, archivo de bloqueo `.app.lock` (creado en `bootstrap.py`, borrado en `app_shell.py::_on_close`) |
| T6.4 Actualización manual desde ZIP (UI) | Hecha | sección "Actualizaciones" en `backups_view.py`, `validate_update_package`/`build_updater_command` |
| T6.5 Actualización obligatoria remota | Diseño documentado, NO codificado (según el plan) | `docs/superpowers/plans/fase-6-operacion-entrega.md`, sección T6.5 |
| T6.6 Scripts de entrega | Escritos, NO ejecutados/verificados (requieren Windows) | `scripts/build_windows.bat`, `scripts/build_updater.bat`, `installer/sistemashn.iss` |
| T6.7 Manual de operación | Hecha | `docs/manual-operacion.md` |

Suite completa tras Fase 6: 680 passed, 1 skipped. Ningún test nuevo en skip/xfail.

### Pendiente antes de vender (fuera del alcance de código de este repo)

- Probar `build_windows.bat`, `build_updater.bat` e `installer/sistemashn.iss` en una PC Windows
  real con Flutter/Visual Studio/Inno Setup — nada de esto se ejecutó en este entorno Linux.
- Generar la clave de producción `core/updater/keys.py`/`tools/vendor/keys/` antes de firmar un
  paquete de actualización para un cliente real (la que hay hoy es de desarrollo).
- Recorrido de aceptación integral de la Fase 6 (ver "Salida de fase" en el plan): activar sin
  internet, crear negocio y administrador, operar el flujo comercial completo, respaldar,
  restaurar en ensayo y actualizar desde un paquete ZIP local firmado — todo en la PC del dueño.
