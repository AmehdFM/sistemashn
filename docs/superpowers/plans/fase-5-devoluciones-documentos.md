# Fase 5 — Anulaciones, devoluciones, documentos y reportes: plan ejecutable

Depende de: Fase 3 (compras, CxP) y Fase 4 (cotizaciones, ventas, caja, CxC). Plan de área
`2026-09-25-devoluciones-documentos.md`, spec `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.
Convenciones de Fases 1-4: servicios con `Actor`/`run_in_transaction`/`authorizer.require`/
auditoría en la misma sesión, idempotencia por `request_id`, numeración por
`comercial/sequences.py`, tipos exactos (`Money/UnitCost/Quantity/Rate`).

## Decisiones de la fase

- **Nunca se borra ni reutiliza numeración**: anular una venta/compra marca `status='anulada'`
  (ya existe la columna en `com_sale`/`com_purchase` desde Fases 3-4, con `CHECK` que ya acepta
  ese valor) y revierte su efecto con movimientos NUEVOS (`MovementKind.VOID_REVERSAL`, ya
  declarado en `comercial/inventario/kinds.py` desde la Fase 2 pero sin uso todavía), nunca
  eliminando ni reescribiendo las filas originales.
- **`void_reversal` genérico**: se agrega `InventoryLedger.void_reversal(session, actor,
  product_id, qty, *, ref_type, ref_id, reason)` que revierte una entrada o salida previa según
  el signo de `qty` (positivo = como una entrada, negativo = como una salida), reutilizando
  internamente `receive`/`issue` con `kind=MovementKind.VOID_REVERSAL` — evita duplicar la lógica
  de promedio ponderado.
- **Anulación de venta**: revierte inventario línea por línea (kits: revierte cada componente),
  revierte el movimiento de caja si lo hubo (`CashService` necesita un
  `register_entry(..., kind="salida")` equivalente o un método `reverse_entry` — decidir la forma
  más simple: un movimiento de signo contrario con `ref_type="void"` referenciando el original),
  y si generó CxC, la cuenta se salda a cero sin abono real (`AccountService` necesita un método
  `void(session, actor, account_id)` interno que ponga `balance=0` y marque de alguna forma que
  fue anulada — la más simple sin migrar el esquema: dejar `balance=0` y no exponer un estado
  "anulada" distinto de "pagada" en `AccountStatus`, documentando la limitación). Requiere
  `com.ventas.anular` (ya declarado en `comercial/module.py` desde la Fase 4, sin perfil asignado
  todavía — se agrega a `gerente`, que ya lo tiene vía `frozenset(p.code for p in _PERMISOS)`).
- **Anulación de compra**: mismo patrón, revierte `ledger.receive` con `void_reversal` (entrada
  negativa) y salda a cero la CxP si la había. Requiere un permiso nuevo `com.compras.anular`
  (agregar a `comercial/module.py`, perfil `gerente`).
- **Restricciones de anulación**: no se anula una venta con caja ya cerrada en la sesión donde se
  cobró en efectivo (evita reescribir un cierre ya conciliado) ni una venta con factura fiscal
  emitida (`FiscalService.get_by_sale` no `None`) — el reglamento exige nota de crédito para eso,
  fuera de alcance; el mensaje de error lo deja explícito. Estas restricciones se verifican antes
  de tocar cualquier estado.
- **Devolución de cliente** (`comercial/devoluciones/`, nuevo paquete): referencia una
  `com_sale_line` original, cantidad parcial acumulada que nunca supera lo vendido en esa línea
  (suma de devoluciones previas de la misma línea + esta ≤ `qty` original). Clasifica la pieza
  devuelta `vendible` (vuelve a `on_hand` con `InventoryLedger.receive` al costo histórico de la
  línea) o `no_vendible` (`move_to_unsellable`). Resuelve con una de tres acciones excluyentes:
  `reembolso` (efectivo/tarjeta/transferencia, requiere caja abierta si es efectivo),
  `cambio` (nueva línea de venta por otro producto, mismo total o con diferencia cobrada/
  reembolsada), `saldo_a_favor` (crea un `com_account` de tipo nuevo — reutiliza `com_account`
  con `kind='credit_note'`, ampliar el `CHECK` de `comercial/credito/models.py` a
  `('payable','receivable','credit_note')`; un saldo a favor es una cuenta con `balance` que el
  cliente puede aplicar a compras futuras, fuera de alcance de esta fase aplicarlo automáticamente
  — solo se registra y se puede consultar/pagar-a-cero manualmente vía `AccountService.pay` como
  ya existe).
- **Devolución a proveedor** (mismo paquete): referencia una `com_purchase_line`, cantidad que no
  supera lo comprado menos lo ya devuelto; saca la unidad de `unsellable` (si venía de una
  devolución de cliente no vendible resuelta hacia el proveedor) o de `on_hand` (defecto detectado
  en bodega) con `InventoryLedger.unsellable_out`/`issue`; el proveedor responde con
  `reemplazo` (entra una unidad nueva al costo de la compra original, sin cambiar CxP),
  `reembolso` (efectivo/no efectivo, no toca CxP) o `credito_futuro` (reduce el saldo de la CxP de
  esa compra si sigue abierta, o crea una nota de crédito de proveedor si ya estaba pagada —
  mismo mecanismo `kind='credit_note'` que arriba pero con `party` proveedor).
- **Documentos PDF**: reutiliza `fpdf2` (ya fijado en ADR-001, con la sonda de
  `core/documents/pdf_probe.py` como base de referencia de fuentes/tamaños 80mm y carta). Un
  módulo nuevo `core/documents/renderer.py` (Core, no Comercial: solo conoce texto/montos/
  estructura genérica de documento, nunca modelos de compra/venta) recibe un `DocumentData`
  (dataclass simple: encabezado del negocio, título, líneas de texto/montos, pie) y produce el
  PDF; `comercial/documentos/` (nuevo, sí puede importar Comercial) arma el `DocumentData` a
  partir de `PurchaseView`/`SaleView`/`QuoteView`/`FiscalInvoiceView` (snapshot al momento de
  emitir: cambios futuros de producto o negocio no alteran un documento ya generado, por eso se
  usan las vistas ya materializadas, nunca una consulta en vivo del catálogo). Impresión con
  `os.startfile(ruta, "print")` en Windows (ya probado en la sonda), degradando sin excepción si
  no hay impresora o el SO no es Windows (`os.name != "nt"`: solo abre/guarda el PDF).
- **Reportes**: `comercial/reportes/` (nuevo) con consultas de solo lectura, sin modelos propios
  (lee directamente `com_sale`/`com_purchase`/`com_account`/`com_cash_session`/`com_stock`).
  Utilidad usa `unit_cost_snapshot` de `com_sale_line` (costo histórico), nunca el costo promedio
  actual del producto. Exporta a Excel reutilizando `openpyxl` como ya hace
  `comercial/catalogo/excel.py` (mismo patrón de escritura, no una librería nueva).

## Permisos (agregar a `COMERCIAL_MODULE`)

`com.ventas.anular` ya existe (Fase 4, sin perfil); asignarlo a `gerente` (ya heredado por
`frozenset(p.code for p in _PERMISOS)`, sin cambio necesario). Nuevos: `com.compras.anular`,
`com.devoluciones.gestionar`, `com.reportes.ver` (grupo nuevo `_GRUPO_REPORTES = "Reportes"`).
Perfil `gerente` recibe todos por herencia automática; `bodega` recibe `com.devoluciones.gestionar`
para devoluciones a proveedor; `vendedor` recibe `com.devoluciones.gestionar` para devoluciones de
cliente (mismo permiso cubre ambos flujos, distinguidos por los datos de la operación, no por
permisos separados — más simple).

## Tareas

### T5.1 Anulaciones (`comercial/ventas/service.py` y `comercial/compras/service.py`, ampliar)

- `SaleService.void(actor, sale_id, reason: str) -> SaleView` (`com.ventas.anular`): valida
  `status='confirmada'`, sin factura fiscal emitida, caja de la venta (si tuvo pago en efectivo)
  sigue `abierta` o no se exige (si la sesión ya cerró, error claro); revierte cada `SaleLine` con
  `ledger.void_reversal`; si generó CxC, la salda; si tuvo movimiento de caja en efectivo, agrega
  un movimiento de caja inverso (salida) referenciando la venta; marca `anulada`; audita
  `com.venta.anulada` con `reason`.
- `PurchaseService.void(actor, purchase_id, reason: str) -> PurchaseView` (`com.compras.anular`):
  mismo patrón, revierte con `void_reversal` (entrada negativa), salda CxP si la había.
- `InventoryLedger.void_reversal(session, actor, product_id, qty, *, ref_type, ref_id, reason)`:
  `qty > 0` revierte una entrada (comportamiento de `issue` sin exigir apartado, aumentando de
  vuelta el promedio ponderado no aplica — en realidad revertir una ENTRADA significa una SALIDA
  de esa cantidad: analiza el caso con cuidado al implementar y documenta la fórmula exacta
  elegida, con pruebas que verifiquen que dos anulaciones simétricas de compra+venta dejan el
  promedio ponderado igual al inicial).
- Pruebas: anular venta al contado revierte stock; anular venta a crédito salda la CxC a cero;
  anular con factura fiscal emitida falla; anular dos veces falla la segunda; anular compra
  revierte promedio ponderado correctamente (verificar con una segunda compra intermedia entre
  medias); permisos.

### T5.2 Devoluciones de cliente (`comercial/devoluciones/`)

- Modelos: `com_customer_return(id, sale_line_id FK com_sale_line.id, qty Quantity, condition
  ('vendible'|'no_vendible'), resolution ('reembolso'|'cambio'|'saldo_a_favor'), amount Money,
  new_sale_id FK com_sale.id nullable — si `resolution='cambio'`, user_id, reason Text, created_at)`.
- `ReturnService.customer_return(actor, data: CustomerReturnInput) -> CustomerReturnView`
  (`com.devoluciones.gestionar`): valida que `qty` + devoluciones previas de esa línea no superen
  la `qty` original; mueve inventario según `condition`; aplica `resolution` (reembolso: registra
  movimiento de caja negativo o pago no efectivo, requiere método de pago; cambio: crea una
  `com_sale` nueva enlazada por `new_sale_id` con la diferencia si la hay; saldo a favor: crea
  `com_account(kind='credit_note')`); todo en una transacción; audita.
- Pruebas: dos devoluciones parciales acumuladas no exceden lo vendido; devolución vendible vs.
  defectuosa afecta el stock correcto; cambio sin stock del producto nuevo falla sin dejar rastro;
  reembolso con caja cerrada falla si el reembolso es en efectivo; saldo a favor consultable.

### T5.3 Devoluciones a proveedor (mismo paquete)

- Modelo: `com_supplier_return(id, purchase_line_id FK com_purchase_line.id, qty Quantity,
  resolution ('reemplazo'|'reembolso'|'credito_futuro'), amount Money, user_id, reason Text,
  created_at)`.
- `ReturnService.supplier_return(actor, data) -> SupplierReturnView` (`com.devoluciones.gestionar`):
  cantidad no supera lo comprado menos lo ya devuelto; saca de `unsellable`/`on_hand` según
  origen; `reemplazo` reingresa unidad al costo original; `credito_futuro` reduce la CxP abierta
  de esa compra o crea `com_account(kind='credit_note')` de proveedor si ya no hay CxP pendiente.
- Pruebas: devolución parcial; crédito aplicado una sola vez (segunda devolución no repite el
  ajuste de la primera); reemplazo actualiza costo promedio correctamente.

### T5.4 Documentos PDF (`core/documents/renderer.py` + `comercial/documentos/`)

- `core/documents/renderer.py`: `DocumentData` (dataclass: `title`, `business_name`,
  `business_address`, `logo_path` opcional, `lines: list[tuple[str, str, str]]` texto/cantidad/
  monto, `totals: list[tuple[str, str]]`, `footer: str`), `render(data, *, paper: Literal["80mm",
  "letter"]) -> bytes` (reutiliza la lógica de `core/documents/pdf_probe.py`, promovida de sonda a
  módulo real — decidir si `pdf_probe.py` se retira o queda como referencia histórica, documentar
  la elección).
- `comercial/documentos/service.py`: `DocumentService.for_quote(quote: QuoteView) ->
  DocumentData`, `.for_purchase(purchase: PurchaseView) -> DocumentData`, `.for_sale(sale: SaleView)
  -> DocumentData` (comprobante interno, título "COMPROBANTE INTERNO — NO FISCAL"), `.for_fiscal_
  invoice(invoice: FiscalInvoiceView, sale: SaleView) -> DocumentData` (usa `snapshot_json` de la
  factura, nunca datos en vivo), `.for_receipt(...)` (recibo de abono, `AccountPaymentView`);
  `save_pdf(data, path, paper)`, `print_pdf(path)` (`os.startfile(path, "print")` en Windows,
  no-op con aviso en otros SO).
- Pruebas: cada `for_*` produce un PDF válido (verificar cabecera `%PDF`) en 80mm y carta; texto
  con acentos/ñ no lanza (reutiliza la fuente ya validada en la sonda); documento generado no
  cambia si el producto/negocio cambian después (snapshot); impresión sin impresora no lanza
  excepción.

### T5.5 Excel y reportes (`comercial/reportes/`)

- `ReportService` (solo lectura, `com.reportes.ver` + `com.costos.ver` donde aplique utilidad):
  `sales_and_profit(actor, since, until) -> SalesProfitReport` (ventas y utilidad con costo
  histórico de `com_sale_line.unit_cost_snapshot`, excluye líneas de ventas `anuladas`), `low_stock
  (actor, page)` (reutiliza `InventoryService.low_stock` ya existente), `account_balances(actor,
  kind)` (reutiliza `AccountService.list`), `cash_closures(actor, since, until)` (lista de
  `CashSessionView` cerradas con diferencia). `export_excel(actor, report_name, params, path)`
  reutilizando el patrón de escritura de `comercial/catalogo/excel.py` (openpyxl, sin librería
  nueva).
- Pruebas: utilidad correcta con costo histórico tras un cambio de costo promedio posterior;
  reporte refleja una anulación (la excluye); rango de fechas vacío no falla; comparación de
  `sales_and_profit` contra el libro de inventario en un escenario con miles de movimientos
  (marcar como prueba lenta si hace falta, seguir el patrón de "1,000 filas < 10 s" de
  `comercial/catalogo/excel.py`).

## Migración

`0004_devoluciones.py`: `com_customer_return`, `com_supplier_return`, ampliación del `CHECK` de
`kind` en `comercial/credito/models.py` (SQLite no soporta `ALTER ... DROP CONSTRAINT`; recrear la
tabla `com_account` con el nuevo `CHECK` vía patrón batch de Alembic — `render_as_batch=True` ya
está configurado en `migrations/env.py`, usar `op.batch_alter_table`). Verificada contra
`tests/core/db/test_schema_matches_models.py`.

## Salida de fase

Suite verde; migración `0004_devoluciones` sobre base con datos de Fase 4; recorrido manual: venta
de dos líneas, devolver parcialmente una defectuosa con saldo a favor, devolver esa unidad al
proveedor con crédito futuro, anular una venta distinta y verificar reverso completo, generar PDF
de cotización/compra/venta en 80mm y carta, exportar reporte de ventas y utilidad a Excel y
verificar cifras contra el libro de inventario. Commit `feat: fase 5 devoluciones documentos y
reportes`.
