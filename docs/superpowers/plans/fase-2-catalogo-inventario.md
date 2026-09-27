# Fase 2 — Catálogo, inventario y Repuestos: plan ejecutable

Depende de: Fase 1. Plan de área `2026-09-25-catalogo-inventario.md`. Convenciones de la Fase 1 (servicios con `Actor`, `run_in_transaction`, `authorizer.require`, `audit` en la misma sesión, `UtcDateTime`, tipos `Money/UnitCost/Quantity/Rate`, `Page`).

## Decisiones de la fase

- **Kits en Comercial** (no en Repuestos): la venta (Comercial) debe expandir kits y Comercial no puede depender de Repuestos. Un kit es un producto con `is_kit=True`, sin fila de existencias propia; su composición vive en `com_kit_component`. La venta guarda la composición y costos aplicados.
- **Equivalencias por grupo**: cada parte tiene `equivalence_group_id` opcional; equivalentes = mismo grupo (transitivo). Vincular dos partes fusiona sus grupos; desvincular saca la parte del grupo.
- **Búsqueda extensible**: Comercial define el protocolo `ProductSearchProvider`; Repuestos registra un proveedor que agrega coincidencias por número de parte, equivalencia y vehículo. El POS usa `CatalogSearchService`, que combina los proveedores registrados.
- Tablas de Comercial con prefijo `com_`, de Repuestos con `rep_`.
- Códigos de producto normalizados: `strip().upper()`, únicos. Búsqueda paginada con `LIKE` sobre columnas indexadas (`code`, `barcode`, `name_search` = nombre en minúsculas sin acentos); suficiente para ~1,000–10,000 productos.

## Permisos (módulo `comercial`)
`com.catalogo.ver`, `com.catalogo.gestionar`, `com.catalogo.importar`, `com.costos.ver`, `com.inventario.ver`, `com.inventario.ajustar`. Perfiles sugeridos: `vendedor` (catalogo.ver, inventario.ver), `bodega` (catalogo.*, inventario.*), `gerente` (todo lo comercial). Módulo `repuestos`: `rep.partes.gestionar`, `rep.vehiculos.gestionar`.

## Tareas

### T2.1 Catálogo (`comercial/catalogo/`)
- Modelos: `com_unit(id, code uq, name, allows_fraction, active)`, `com_category(id, name uq, active)`, `com_product(id, code uq, barcode uq nullable, name, name_search ix, description, category_id FK nullable, unit_id FK, tax_rate Rate, sale_price Money, min_stock Quantity, is_kit, active, created_at, updated_at)`. CHECK `sale_price >= 0`, `tax_rate IN (0, 1500, 1800)` (valor escalado).
- `normalize_search(text) -> str` (minúsculas, sin acentos con `unicodedata`).
- `CatalogService(factory, authorizer, clock)`: `create_unit/update_unit/list_units`, `create_category/...`, `create_product(actor, data: ProductInput) -> int`, `update_product`, `set_active(actor, id, active)` (inactivar con historial se permite; borrar nunca), `get_product(actor, id) -> ProductView` (costo promedio solo si `com.costos.ver`, si no `None`), `search(actor, text, *, page, page_size, include_inactive=False) -> Page[ProductView]`, `find_by_code_or_barcode(actor, code) -> ProductView | None` (lector USB). Pydantic `ProductInput` (código no vacío ≤ 40, nombre ≤ 200, precio ≥ 0, tasa ∈ {0, 0.15, 0.18}). Al crear producto no kit crea su fila `com_stock` en cero. Auditoría de alta/edición/inactivación con antes/después de precio.
- Pruebas: duplicado de código y barcode (con normalización), código vacío, tasa inválida, fraccionario según unidad (lo valida el ledger), búsqueda por nombre con/sin acentos y por código, paginación, costo oculto sin permiso, inactivar producto con movimientos.

### T2.2 Libro de inventario (`comercial/inventario/`)
- Modelos: `com_stock(product_id PK FK, on_hand Quantity, reserved Quantity, unsellable Quantity, avg_cost UnitCost, updated_at)` con CHECK `on_hand >= 0`, `reserved >= 0`, `unsellable >= 0`, `reserved <= on_hand`. `com_stock_movement(id, product_id ix, occurred_at, kind, d_on_hand, d_reserved, d_unsellable, unit_cost UnitCost nullable, avg_cost_after UnitCost, ref_type, ref_id, user_id, reason)` append-only (triggers como auditoría).
- `MovementKind` (StrEnum): `purchase_in`, `sale_out`, `reserve`, `release`, `customer_return_sellable`, `customer_return_unsellable`, `supplier_return_out`, `unsellable_resolved`, `adjustment_in`, `adjustment_out`, `void_reversal`.
- `InventoryLedger` (API **interna**, recibe la `session` de la operación de negocio; no abre transacciones ni verifica permisos, eso lo hace el servicio llamador): `receive(session, actor, product_id, qty, unit_cost, ref) -> Decimal` (promedio ponderado: si on_hand ≤ 0 → avg = cost; si no `(on_hand*avg + qty*cost)/(on_hand+qty)` cuantizado a 4 dec), `issue(session, actor, product_id, qty, ref) -> Decimal` (sale de disponible `on_hand - reserved`, devuelve costo promedio aplicado; insuficiente → `InsufficientStock(product_id, disponible, pedido)`), `reserve/release(...)`, `issue_reserved(...)` (consume apartado), `move_to_unsellable/from_unsellable`, `adjust(...)`. Valida cantidad > 0 y fracción según `unit.allows_fraction`. Kits: `ledger` rechaza productos kit (los expande el servicio de ventas con `KitService`).
- `InventoryService(factory, authorizer, clock)`: `adjust(actor, product_id, delta, reason)` (requiere `com.inventario.ajustar`, motivo obligatorio ≥ 5 chars, audita), `stock(actor, product_id) -> StockView`, `movements(actor, product_id, page) -> Page`, `low_stock(actor, page)`, `reconcile(product_id) -> bool` (suma de movimientos == saldo; usado por pruebas y reportes).
- Pruebas: promedio con compras a distintos costos y fraccionarias; stock cero y recompra; salida insuficiente no deja nada; apartado reduce disponible pero no físico; saldo nunca negativo (también CHECK directo en base); fallo en la segunda de dos salidas dentro de la misma transacción revierte ambas; movimientos inmutables; reconciliación.

### T2.3 Kits (`comercial/catalogo/kits.py`) (∥ con T2.4)
- `com_kit_component(kit_id FK, component_id FK, qty Quantity, PK compuesta)`.
- `KitService`: `set_components(actor, kit_id, components: list[(id, qty)])` (componentes activos, no kits → sin ciclos ni anidación en v1, qty > 0, al menos 1; audita), `components(kit_id)`, `availability(session, kit_id) -> Decimal` (mínimo de `disponible(componente)/qty`, truncado a entero si alguna unidad no es fraccionaria), `explode(session, kit_id, qty) -> list[KitLine(component_id, qty, avg_cost)]` para la venta.
- Pruebas: componente inactivo/kit/cantidad cero rechazados; disponibilidad mínima; explode con costos; cambio posterior de composición no altera datos devueltos antes (la venta guardará snapshot en Fase 4).

### T2.4 Repuestos (`repuestos/partes/`, `repuestos/vehiculos/`) (∥ con T2.3)
- Modelos: `rep_part(product_id PK FK com_product, part_number, part_number_search ix, manufacturer, origin ('original'|'generico'), equivalence_group_id nullable ix)`, `rep_vehicle_make(id, name uq)`, `rep_vehicle_model(id, make_id, name, uq(make_id,name))`, `rep_compatibility(id, product_id, model_id, year_from, year_to, CHECK year_from <= year_to, CHECK 1950–2100)`.
- `PartService`: `set_part_info`, `link_equivalent(a, b)` (fusiona grupos), `unlink(product)`, `equivalents(product_id)`, `add_compatibility`, `remove_compatibility`, `compatible_products(make, model, year, page)`. `VehicleService` para marcas/modelos.
- `RepuestosSearchProvider` implementa `ProductSearchProvider.search(session, text, limit) -> list[int]` (ids) por número de parte normalizado (sin guiones/espacios) y sus equivalentes.
- `REPUESTOS_MODULE: ModuleDef` con permisos y pantallas `/repuestos/vehiculos`.
- Pruebas: parte compartida entre marcas; años en extremos; equivalencia duplicada idempotente; fusión transitiva; búsqueda "ph16" encuentra "PH-16" y su equivalente; producto inactivo excluido.

### T2.5 Excel (`comercial/catalogo/excel.py`)
- Plantilla: hoja "Productos" con encabezados `codigo, codigo_barras, nombre, descripcion, categoria, unidad, tasa_isv (0|15|18), precio_venta, stock_minimo, activo (si|no)`; Repuestos agrega columnas opcionales `numero_parte, fabricante, origen` mediante un hook `extra_columns` registrado por el módulo.
- `ExcelImportService`: `preview(actor, path) -> ImportPreview(filas_validas, errores[(fila, columna, mensaje)], nuevos, actualizados)` sin escribir; `commit(actor, preview, policy='solo_validas'|'todo_o_nada')` en una transacción; idempotente por `codigo` (reintento no duplica). Rechaza fórmulas (celdas cuyo valor empieza por `=` o `data_type == 'f'`), archivo corrupto, columnas faltantes. Categorías/unidades inexistentes → error de fila (no se crean implícitamente). `export_products(actor, path)` y `write_template(path)`. Importar no toca existencias (eso es compra/ajuste).
- Pruebas: 1,000 filas < 10 s; acentos; fila con precio texto; columnas faltantes; fórmula; reimportación idempotente; export → import produce los mismos productos.

### T2.6 Pantallas
- `comercial/ui/`: catálogo (búsqueda con debounce, tabla paginada, formulario alta/edición, inactivar), detalle con existencias y movimientos, ajuste de inventario (con motivo), stock bajo, unidades/categorías, importación Excel (elegir archivo con `ft.FilePicker`, vista previa de errores, confirmar), kits. `repuestos/ui/`: pestaña de datos de parte/equivalencias/compatibilidad dentro del formulario de producto (hook de extensión de formulario registrado por Repuestos), pantalla de vehículos.
- Hook de extensión: Comercial define `ProductFormExtension` (protocolo con `build(ctx, product_id) -> ft.Control` y `save(...)`); Repuestos registra la suya. `app/repuestos.py` compone.
- Teclado: Enter en búsqueda abre el primer resultado; lector USB (código + Enter) resuelve por `find_by_code_or_barcode`.

## Salida de fase
Suite verde; migración `0002_comercial_repuestos` sobre base con datos de Fase 1; recorrido manual: crear unidades/categorías, importar 1,000 productos de ejemplo (`scripts/generar_catalogo_demo.py`), asociar partes/equivalencias/vehículos, ajustar inventario, ver stock bajo; medir búsqueda (< 300 ms en esta PC). Commit `feat: fase 2 catalogo inventario repuestos`.
