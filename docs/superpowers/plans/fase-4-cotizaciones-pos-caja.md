# Fase 4 — Cotizaciones, POS, pagos, caja y cuentas por cobrar: plan ejecutable

Depende de: Fase 2 (catálogo, inventario, kits) y Fase 3 (contrapartes, idempotencia,
numeración, `AccountService`, métodos de pago). Plan de área
`2026-09-25-cotizaciones-pos-caja.md`, spec `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`,
investigación fiscal `docs/investigacion-facturacion-honduras.md`. Convenciones de Fases 1-3:
servicios con `Actor`/`run_in_transaction`/`authorizer.require`/auditoría en la misma sesión,
`Money/UnitCost/Quantity/Rate`, `UtcDateTime`, idempotencia por `request_id`, numeración por
`comercial/sequences.py`.

## Decisiones de la fase

- **Reutilizar `comercial/credito`** para cuentas por cobrar: mismo modelo `com_account` /
  `com_account_payment` que ya usan las cuentas por pagar (`AccountKind.RECEIVABLE`,
  permisos `com.cxc.ver`/`com.cxc.cobrar` ya declarados en `comercial/module.py` desde la
  Fase 3). No se crea un paquete nuevo de CxC.
- **Apartado como reserva de inventario**: una cotización con apartado llama
  `InventoryLedger.reserve` por línea (no kits: se reserva cada componente del kit, ver más
  abajo) al guardarla; al vencer, cancelarla o convertirla, se llama `release`. El vencimiento
  se comprueba de forma perezosa (al listar/abrir una cotización o al iniciar una operación que
  toque esa reserva), nunca con un temporizador en segundo plano — coincide con la spec
  ("no depende de que la PC esté encendida a la hora exacta del vencimiento").
- **Kits en la venta**: la venta nunca llama `InventoryLedger` directamente sobre un producto
  `is_kit=True`; usa `sistemashn.comercial.catalogo.kits.explode(session, kit_id, qty)` para
  obtener las líneas de componente (con su costo promedio actual) y aplica `issue`/`issue_reserved`
  componente por componente. La venta guarda un snapshot de la composición y el costo aplicado
  en cada línea de kit vendida (no depende de que el kit no cambie después).
- **Comprobante interno vs. factura legal**: toda venta genera un comprobante interno (numeración
  propia `V-000001`), sea o no fiscal. La factura fiscal (T4.5) es un documento aparte, opcional,
  vinculado 1:1 a una venta, con su propio correlativo (`NNN-NNN-NN-NNNNNNNN`), deshabilitada por
  defecto (`core_business.fiscal_enabled = False`). Ningún texto de la UI ni de este plan afirma
  cumplimiento fiscal: ver "Reglas para la primera implementación" de la investigación.
- **Pagos mixtos**: reutiliza `comercial/pagos/methods.py` (`PaymentInput`, `PaymentMethod`) tal
  cual. El vuelto (`change`) solo aplica si el pago incluye efectivo y la suma de todos los
  métodos excede el total; se calcula sobre el excedente de efectivo únicamente (tarjeta/
  transferencia no generan vuelto). Si la suma de pagos es menor al total, el resto es crédito
  (misma regla que compras) y exige `credit_due_date`.
- **Caja como control de turno, no como cuenta contable**: una `com_cash_session` por apertura/
  cierre (un usuario, un período); los pagos en efectivo de ventas/abonos se enlazan a la sesión
  de caja abierta en ese momento (si la política exige caja abierta y no la hay, la venta con
  componente en efectivo se rechaza — pagos no efectivo no la requieren). Entradas/salidas
  manuales (retiro, depósito, gasto) quedan como movimientos de caja con motivo. El cierre
  compara el efectivo esperado (apertura + entradas − salidas + cobros en efectivo) contra el
  contado físico y registra la diferencia; no ajusta el inventario ni las cuentas.
- **Conversión de cotización a venta**: se revalida disponibilidad y precio actual contra el
  catálogo en el momento de convertir; si hay diferencias, la conversión se detiene y devuelve
  esas diferencias para que la UI las muestre — no confirma una venta con datos obsoletos sin que
  el empleado decida explícitamente continuar (segunda llamada, ya informado, con los mismos
  datos u otros ajustados).
- **CAI deshabilitado por defecto**: `core_business.fiscal_enabled` (ya existe en el modelo desde
  Fase 1/A) controla si la pantalla de venta ofrece "Emitir factura fiscal". El modelo y servicio
  de autorizaciones CAI se implementan y prueban igual, pero la UI y el `README`/manual dejan
  explícito que es "pendiente de validación fiscal" (texto literal en la pantalla).

## Permisos (módulo `comercial`, añadir a `COMERCIAL_MODULE`)

`com.cotizaciones.ver`, `com.cotizaciones.gestionar`, `com.ventas.ver`, `com.ventas.registrar`,
`com.ventas.anular` (declarado ahora, usado en Fase 5), `com.caja.ver`, `com.caja.operar`,
`com.caja.cerrar`, `com.fiscal.gestionar` (administra autorizaciones CAI). `com.cxc.ver` y
`com.cxc.cobrar` ya existen desde la Fase 3. Perfil `vendedor` recibe
cotizaciones.ver/gestionar, ventas.ver/registrar, caja.ver/operar, cxc.ver/cobrar; `gerente`
todo, incluida caja.cerrar y fiscal.gestionar.

## Tareas

### T4.1 Cotizaciones y apartados (`comercial/cotizaciones/`)

- Modelos: `com_quote(id, uuid uq, number uq, customer_id FK com_party.id nullable, status
  ('abierta'|'convertida'|'cancelada'|'vencida'), valid_until Date, has_reservation Boolean,
  subtotal Money, tax_total Money, total Money, user_id, notes nullable, created_at)`,
  `com_quote_line(id, quote_id FK, line_no, product_id FK com_product.id, description_snapshot,
  qty Quantity, unit_price Money, tax_rate Rate, line_subtotal Money, line_tax Money, line_total
  Money)`.
- `QuoteService`: `create(actor, data: QuoteInput) -> QuoteView` (`com.cotizaciones.gestionar`,
  numeración `Q-000001`; si `data.reserve=True`, reserva cada línea — kits: reserva cada
  componente proporcional, rechaza si algún componente no alcanza; todo en una transacción, si
  falla una línea no reserva nada); `cancel(actor, quote_id)` (libera reservas si las había,
  marca `cancelada`); `get(actor, quote_id)` (si `status='abierta'` y `valid_until` ya pasó,
  libera reservas y marca `vencida` de forma perezosa antes de devolver la vista — mismo patrón
  perezoso que usa `AccountService._status` para "vencida"); `list(actor, filtros, page)`;
  `release_expired(session)` función interna reutilizable desde otros puntos de entrada
  (arranque de la app, apertura de POS) para no depender de que alguien abra esa cotización en
  particular.
- Pruebas: reserva de línea simple y de kit; apartado con stock insuficiente no reserva nada;
  vencimiento libera al consultar; cancelar libera; dos cotizaciones compitiendo por el mismo
  stock (la segunda reserva lo que queda o falla); cantidad fraccionaria; liberar dos veces no
  falla ni duplica.

### T4.2 Ventas y comprobante interno (`comercial/ventas/`)

- Modelos: `com_sale(id, uuid uq, number uq, quote_id FK com_quote.id nullable, customer_id FK
  com_party.id nullable, sold_at, subtotal Money, tax_total Money, total Money, paid_amount
  Money, change_amount Money, credit_amount Money, status ('confirmada'|'anulada'), user_id,
  cash_session_id FK com_cash_session.id nullable, notes nullable, created_at)`,
  `com_sale_line(id, sale_id FK, line_no, product_id FK com_product.id, description_snapshot,
  qty Quantity, unit_price Money, tax_rate Rate, line_subtotal Money, line_tax Money, line_total
  Money, unit_cost_snapshot UnitCost, kit_component_of INTEGER nullable — referencia a la línea
  de kit que generó esta línea de componente, o NULL si es una línea normal/kit vendida
  directamente)`, `com_sale_payment(id, sale_id FK, method, amount Money, reference nullable)`.
- `SaleInput` (Pydantic): `customer_id` opcional, `quote_id` opcional, `lines[(product_id, qty,
  unit_price opcional → precio de catálogo)]`, `payments[PaymentInput]`, `credit_due_date`
  opcional, `cash_session_id` opcional, `notes`, `request_id`.
- `SaleService.confirm(actor, data) -> SaleView` (`com.ventas.registrar`), en UNA transacción:
  idempotencia; por cada línea: si el producto es kit, `kits.explode` y `ledger.issue` (o
  `issue_reserved` si viene de una cotización con apartado) por cada componente, guardando una
  `SaleLine` por componente con `kit_component_of` apuntando a la línea de kit; si no es kit,
  `issue`/`issue_reserved` directo. Si `quote_id` viene, revalida contra el catálogo actual
  (precio, disponibilidad) ANTES de tocar inventario — si hay diferencias y el llamador no pasó
  una bandera explícita `accept_changes=True` en `SaleInput`, la operación no confirma nada y
  devuelve `QuoteConversionMismatch(differences)` con el detalle; con `accept_changes=True` sigue
  con los datos que trae `data.lines` (los que decidió la UI tras mostrar el aviso). Calcula
  pagos/vuelto/crédito con la misma lógica de compras (mixtos, vuelto solo si hay efectivo y el
  total de pagos excede el total de la venta); si crédito > 0 crea cuenta por cobrar vía
  `AccountService.create_account(kind=RECEIVABLE, source_type="sale", ...)`; si `quote_id` venía
  con apartado, consume el apartado (`issue_reserved`) en vez de reservar de nuevo; marca la
  cotización `convertida`. Número `V-000001`. Auditoría `com.venta.confirmada`.
- Consultas: `get`, `list(filtros: cliente/fecha/texto/estado, page)`, `history(customer_id,
  page)`.
- Pruebas: venta simple al contado; venta de kit (snapshot de composición y costo histórico
  correcto, línea por componente); pagos mixtos con vuelto solo por el excedente de efectivo;
  venta a crédito crea CxC; conversión de cotización con apartado consume el apartado sin volver
  a reservar; conversión con cambio de precio/stock detenida sin `accept_changes`, confirmada con
  la bandera; kit sin stock suficiente en algún componente falla sin dejar rastro (ni la venta, ni
  movimientos de los demás componentes ya procesados); reintento idempotente; permisos.

### T4.3 Pagos, crédito y caja (`comercial/caja/`)

- Modelos: `com_cash_session(id, opened_at, closed_at nullable, opened_by user_id, closed_by
  user_id nullable, opening_amount Money, expected_cash Money nullable, counted_cash Money
  nullable, difference Money nullable, status ('abierta'|'cerrada'), notes nullable)`,
  `com_cash_movement(id, cash_session_id FK, occurred_at, kind ('entrada'|'salida'|'venta'|
  'abono'), amount Money, reason nullable, ref_type nullable, ref_id nullable, user_id)`
  (append-only, mismo patrón de trigger que auditoría/movimientos de inventario).
- `CashService`: `open(actor, opening_amount) -> CashSessionView` (`com.caja.operar`, rechaza si
  ya hay una sesión abierta), `register_entry(session, actor, amount, reason, ref)` /
  `register_exit(...)` (uso interno desde ventas/abonos en efectivo, y `manual_entry`/
  `manual_exit(actor, amount, reason)` públicos con permiso), `close(actor, counted_cash) ->
  CashSessionView` (`com.caja.cerrar`, calcula `expected_cash` sumando movimientos, guarda
  `difference = counted_cash - expected_cash`), `current(actor) -> CashSessionView | None`,
  `movements(actor, cash_session_id, page)`. `SaleService`/`AccountService.pay` llaman
  `register_entry` cuando el método de pago es efectivo y hay caja abierta; si la política exige
  caja (`core_business` u opción de ajustes, decidir el flag más simple: `cash_session_required:
  bool` en `core_business`, default `True`) y no hay sesión abierta, la venta/abono con
  componente en efectivo se rechaza con un error claro antes de tocar inventario o cuentas.
- Pruebas: apertura/cierre normal; cierre con diferencia positiva y negativa; abrir con sesión ya
  abierta falla; venta en efectivo sin caja abierta falla (política activada) y no falla
  (desactivada); entradas/salidas manuales requieren motivo; conciliación summa movimientos ==
  `expected_cash`.

### T4.4 Cuentas por cobrar

- No hay tarea de código nueva: se reutiliza `comercial/credito/service.py::AccountService` con
  `AccountKind.RECEIVABLE`. Verificar (y completar si falta) que los permisos `com.cxc.ver`/
  `com.cxc.cobrar` cubren el flujo desde `SaleService` igual que `com.cxp.*` cubre compras.
- Pruebas: si `AccountService` ya cubre genéricamente pagar/listar por `kind`, basta una prueba de
  integración en `comercial/ventas/test_service.py` que confirma que una venta a crédito crea la
  cuenta y que un abono vía `AccountService.pay` la salda; no se duplican las pruebas unitarias de
  `AccountService` ya existentes en `tests/comercial/credito/`.

### T4.5 Factura legal (CAI) — implementada pero deshabilitada

- Modelos: `com_fiscal_authorization(id, cai String uq, document_type ('factura'), range_start
  String, range_end String, valid_until Date, next_correlative Integer, status ('activa'|
  'agotada'|'vencida'))`, `com_fiscal_invoice(id, sale_id FK com_sale.id uq, authorization_id FK,
  fiscal_number String uq — formato `NNN-NNN-NN-NNNNNNNN`, issued_at, snapshot_json Text —
  copia de los datos legales al momento de emitir, per art. 10-11 de la investigación)`.
- `FiscalService`: `register_authorization(actor, data)` (`com.fiscal.gestionar`), `issue(actor,
  sale_id) -> FiscalInvoiceView` (rechaza si `core_business.fiscal_enabled` es `False`, si no hay
  autorización `activa` para el tipo, si el rango está agotado o `valid_until` ya pasó — nunca
  permite forzar fuera de rango, ver "Reglas para la primera implementación" de la
  investigación), consume `next_correlative` dentro de la transacción (mismo patrón que
  `comercial/sequences.py` pero en su propia tabla, ya que el correlativo fiscal tiene formato y
  vigencia propios, no es un `com_sequence` genérico).
- Pruebas: emitir con autorización válida; rechazado con `fiscal_enabled=False`; rango agotado;
  autorización vencida; dos emisiones para la misma venta rechazadas (unicidad `sale_id`).
- **No se activa en la UI de venta por defecto**: el botón "Emitir factura fiscal" solo aparece si
  `fiscal_enabled=True` Y hay una autorización activa, y siempre lleva la etiqueta "pendiente de
  validación fiscal" (ver decisión de fase). No se afirma cumplimiento fiscal en ningún texto.

### T4.6 Pantallas

- **POS** (`/pos`): búsqueda por código/nombre/parte/equivalencia (usa `CatalogSearchService` ya
  existente, combinando proveedores registrados) con soporte de lector USB (código + Enter,
  mismo patrón que `catalog_view.py._on_submit`); líneas con cantidad editable; totales en vivo;
  selector de cliente opcional (busca con `parties.search(role="customer")`, mismo patrón que el
  selector de proveedor de "nueva compra"); pagos mixtos con cálculo de vuelto en vivo; resumen de
  confirmación antes de aplicar; tras confirmar, opción de imprimir/ver comprobante (la
  generación real de PDF es Fase 5 — por ahora solo el resumen en pantalla).
- **Cotizaciones** (`/cotizaciones`): lista con estado (abierta/vencida/convertida/cancelada) y
  filtro; formulario de captura (mismo patrón de líneas por código que compras/POS) con checkbox
  "Apartar inventario" y fecha de vigencia; acción "Convertir a venta" que llama al flujo de
  conversión y muestra el aviso de diferencias si las hay antes de confirmar.
- **Ventas / historial** (`/ventas`): lista con filtros (cliente, fecha, texto), detalle de solo
  lectura (mismo patrón que el detalle de compra).
- **Caja** (`/caja`): estado actual (abierta/cerrada), botón abrir con monto inicial, entradas/
  salidas manuales con motivo, botón cerrar con conteo físico y diferencia mostrada, historial de
  sesiones anteriores.
- **Cuentas por cobrar** (`/cxc`): mismo patrón que `cxp_view.py` pero con `AccountKind.RECEIVABLE`
  y permisos `com.cxc.*` (puede factorizarse un componente compartido `accounts_view` parametrizado
  por `kind`/permisos/título si al implementar resulta más simple que duplicar `cxp_view.py`;
  decisión de quien implemente, documentarla).
- Registrar las 5 rutas nuevas (`/pos`, `/cotizaciones`, `/ventas`, `/caja`, `/cxc`) en
  `comercial/module.py` (`_PANTALLAS`) y sus builders en `comercial/ui/screens.py`.

## Migración

`0003_ventas.py`: todas las tablas nuevas de T4.1-T4.5 (`com_quote`, `com_quote_line`,
`com_sale`, `com_sale_line`, `com_sale_payment`, `com_cash_session`, `com_cash_movement` con
trigger append-only, `com_fiscal_authorization`, `com_fiscal_invoice`), verificada contra
`tests/core/db/test_schema_matches_models.py`.

## Salida de fase

Suite verde; migración `0003_ventas` sobre base con datos de Fase 3; recorrido manual: cotizar
con apartado, dejarla vencer y ver que libera, cotizar de nuevo y convertir con aviso de cambio de
precio, vender un kit y una pieza suelta con pagos mixtos y vuelto, abrir/cerrar caja con
diferencia, crear una venta a crédito y abonarla dos veces, verificar que "Emitir factura fiscal"
no aparece sin autorización configurada. Commit `feat: fase 4 cotizaciones pos caja y cxc`.
