# Fase 3 — Compras, proveedores y cuentas por pagar: plan ejecutable

Depende de: Fase 2 (`InventoryLedger.receive`, catálogo). Plan de área `2026-09-25-compras-credito.md`. Convenciones de Fases 1–2.

## Decisiones de la fase

- **Contraparte única** `com_party` (persona o negocio) con banderas `is_supplier`, `is_customer`. La deduplicación es asistida: el servicio sugiere posibles duplicados (RTN igual o nombre normalizado igual) pero nunca fusiona automáticamente.
- **Métodos de pago** (compartidos con ventas, Fase 4): `PaymentMethod` StrEnum `efectivo`, `tarjeta`, `transferencia`. Se definen en `comercial/pagos/methods.py`.
- **Idempotencia**: toda operación que crea un documento económico recibe `request_id: str` (uuid generado por la UI al abrir el formulario). Tabla `com_idempotency(request_id PK, operation, result_ref, created_at)`: si el `request_id` ya existe, el servicio devuelve el resultado anterior sin repetir la operación. Helper común en `comercial/idempotency.py`.
- **Numeración interna** de documentos: tabla `com_sequence(name PK, next_value)`; `next_number(session, name) -> int` dentro de la transacción del documento (BEGIN IMMEDIATE garantiza unicidad). Formato visible `C-000123` (compras). Un número consumido nunca se reutiliza (si la transacción se revierte, no se consumió).
- La compra no se edita ni se borra una vez confirmada (anulación en Fase 5). No hay borradores persistentes en v1: la UI mantiene el borrador en memoria hasta confirmar.
- Costo de compra por línea = costo unitario **sin ISV** (el ISV de compras es crédito fiscal, fuera de alcance contable). Se guarda `tax_rate` e ISV por línea para el documento.

## Permisos (módulo `comercial`, añadir a `COMERCIAL_MODULE`)
`com.contrapartes.ver`, `com.contrapartes.gestionar`, `com.compras.ver`, `com.compras.registrar`, `com.cxp.ver`, `com.cxp.pagar`. Perfil `bodega` recibe contrapartes.ver/gestionar y compras.ver/registrar; `gerente` todo.

## Tareas

### T3.1 Contrapartes (`comercial/contrapartes/`)
- `com_party(id, kind ('persona'|'negocio'), name, name_search ix, rtn nullable ix (14 dígitos), phone, email, address, is_supplier, is_customer, active, notes, created_at, updated_at)`.
- `PartyService`: `create(actor, data, *, allow_duplicate=False)` → si hay posibles duplicados y no `allow_duplicate`, lanza `PossibleDuplicate(candidates)` (ValidationError con lista); `update`, `set_roles(actor, id, supplier, customer)`, `set_active`, `get`, `search(actor, text, role=None, page)`, `find_duplicates(session, name, rtn)`.
- Pruebas: RTN inválido; nombre coincidente sugiere pero no fusiona; `allow_duplicate` crea; proveedor que luego es cliente; búsqueda por nombre sin acentos y por RTN; permisos.

### T3.2 Compras (`comercial/compras/`)
- Modelos: `com_purchase(id, uuid uq, number uq, supplier_id FK, supplier_invoice_ref nullable, purchased_at, subtotal Money, tax_total Money, total Money, paid_initial Money, credit_amount Money, status ('confirmada'|'anulada'), user_id, notes, created_at)`, `com_purchase_line(id, purchase_id, line_no, product_id, description_snapshot, qty Quantity, unit_cost UnitCost, tax_rate Rate, line_subtotal Money, line_tax Money, line_total Money)`, `com_purchase_payment(id, purchase_id, method, amount Money, reference nullable)`, `com_supplier_price(id, supplier_id, product_id, unit_cost, purchase_id, recorded_at)` (histórico, una fila por línea).
- `PurchaseInput` (Pydantic): supplier_id, supplier_invoice_ref, lines[(product_id, qty, unit_cost, tax_rate opcional → la del producto)], payments[(method, amount, reference)], credit_due_date opcional, notes, request_id.
- `PurchaseService.confirm(actor, data) -> PurchaseView` (`com.compras.registrar`), en UNA transacción: idempotencia; proveedor activo con `is_supplier`; productos activos no kit; cálculos por línea con `money()` (subtotal = qty × unit_cost redondeado; ISV = subtotal × tasa redondeado; total = suma); pagos > 0 y suma ≤ total; si suma < total exige `credit_due_date` ≥ fecha de compra y crea la cuenta por pagar (T3.3) por la diferencia; `ledger.receive` por línea con `ref_type="purchase"`; `com_supplier_price` por línea; número `C-000001`; auditoría `com.compra.confirmada` con totales.
- Consultas: `get(actor, id)`, `list(actor, filtros(proveedor, desde, hasta, texto), page)`, `supplier_history(actor, supplier_id, page)`, `last_prices(actor, product_id, limit=10)` (requiere `com.costos.ver`).
- Pruebas: compra de 2 productos al contado con promedio comprobado; compra a crédito crea CxP; pagos mixtos; pagos que exceden total; crédito sin vencimiento; proveedor inactivo o que no es proveedor; producto kit; fallo inducido en la última línea (producto inactivo al final) → nada persiste (ni stock, ni CxP, ni número consumido, ni auditoría); reintento con mismo request_id no duplica; historial de precios intacto tras nueva compra a otro precio; vendedor sin permiso; costos ocultos.

### T3.3 Cuentas por pagar (`comercial/credito/`)
- Diseño común para CxP y CxC (Fase 4): `com_account(id, kind ('payable'|'receivable'), party_id, source_type, source_id, original_amount Money, due_date, created_at, status derivado)` y `com_account_payment(id, account_id, paid_at, method, amount Money, reference, user_id, request_id uq)`. Saldo = original − suma de abonos (calculado, y cacheado en `balance Money` actualizado en la misma transacción; prueba de reconciliación). Estados derivados: `pendiente`, `vencida` (hoy > due_date y saldo > 0), `pagada`.
- `AccountService`: `create_payable(session, actor, party_id, source, amount, due_date)` (interna), `pay(actor, account_id, method, amount, reference, request_id)` (`com.cxp.pagar` para payable; `com.cxc.cobrar` para receivable, que se registrará en Fase 4), valida 0 < amount ≤ saldo, audita; `list(actor, kind, filtros(estado, contraparte), page)`, `get(actor, id)` con abonos; `party_balance(actor, party_id, kind)`.
- Pruebas: dos abonos y saldo exacto; abono que excede; cero/negativo; reintento duplicado; vencida por reloj; pagada; reconciliación balance vs abonos.

### T3.4 Pantallas
- Contrapartes (lista + formulario con aviso de duplicados), Nueva compra (proveedor con búsqueda, líneas con búsqueda de producto por código/lector, cantidades y costo, totales en vivo con `money`, pagos mixtos, crédito con vencimiento, resumen de confirmación antes de aplicar), Historial de compras (filtros, detalle), Cuentas por pagar (lista con estados y abono en diálogo). Últimos precios del proveedor visibles al capturar la línea si hay `com.costos.ver`.
- Toda llamada de confirmación genera `request_id` al abrir el formulario y lo conserva en reintentos.

## Salida de fase
Suite verde; migración `0003_compras` sobre base con datos de Fase 2; recorrido manual: crear proveedor, compra a crédito de 2 productos con pago inicial mixto, dos abonos hasta saldar, ver historial y precios anteriores, verificar costo promedio en catálogo. Commit `feat: fase 3 compras y cuentas por pagar`.
