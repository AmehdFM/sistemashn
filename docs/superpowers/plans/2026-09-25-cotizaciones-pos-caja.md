# Cotizaciones, ventas, crédito y caja: plan de área

**Meta:** pasar de una cotización guardada a una venta segura, con apartado opcional, factura genérica o legal, pagos mixtos, crédito y caja. **Depende de:** catálogo, compras y Core. **Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.

## Invariantes de operación

Toda factura recibe ID y número interno irrepetible; CAI es dato adicional opcional para la modalidad legal. Una venta confirmada conserva líneas, precios, descuentos/impuestos, costo histórico, composición de kit, pagos, movimiento de caja/inventario, usuario y vínculo a cotización dentro de una transacción. Se reserva numeración con una política explícita ante rollback/anulación; nunca se reutiliza un número emitido. La cotización retiene el precio ofrecido, pero la conversión muestra cambios de precio y disponibilidad y requiere decisión informada del empleado.

## Tareas

- [ ] **Cotización.** Guardar cliente opcional, líneas, precios y vencimiento. Permitir apartado sí/no por cotización; reservar solo unidades disponibles y liberarlas al vencer/cancelar/conversión. Probar cierre de app durante el vencimiento, dos cotizaciones competidoras, cantidad fraccionaria y liberación repetida.
- [ ] **Conversión.** Mostrar diferencias frente al catálogo actual, respetar precio cotizado al continuar, impedir stock insuficiente y confirmar liberación/consumo del apartado con la venta. Probar cotización alterada por otro usuario entre previsualización y confirmación.
- [ ] **POS.** Búsqueda por código, nombre, parte/equivalencia y lector USB tipo teclado opcional. Cálculos exactos y validación en servicio. Diferenciar comprobante interno no fiscal y factura fiscal autoimpresa: el segundo requiere inscripción/autorización del negocio, CAI, rango, vigencia y correlativo separado del ID interno. Aplicar la [investigación fiscal](../../investigacion-facturacion-honduras.md) y verificar normativa/caso real antes de habilitar emisión fiscal en producción. Probar doble confirmación, kit sin componente, rango agotado/vencido y venta sin conexión.
- [ ] **Pagos y crédito.** Efectivo, tarjeta, transferencia y mezcla; recibido/vuelto solo para efectivo, suma aplicada igual a contado o inicial de crédito. Cuentas por cobrar con vencimiento y abonos parciales con historial; impedir saldo negativo o aplicación duplicada. Probar reintento de confirmación y redondeo al centavo.
- [ ] **Caja.** Apertura/cierre por usuario autorizado, entradas/salidas y conciliación de pagos en efectivo frente a métodos electrónicos. Evitar pago de venta sin caja cuando la política exige sesión activa. Probar cierre con diferencia, venta anulada y día siguiente.
- [ ] **Pantallas y auditoría.** Mostrar estados pendientes, vencidos y errores; ocultar cobros/caja/legal sin permiso y rechazar llamadas directas al servicio. Consultas paginadas e historial separado de venta y anulación.

## Evidencia de salida

Cotizar y apartar; dejar vencer y liberar; cotizar de nuevo y convertir con advertencia de cambio; vender pieza y kit con pagos mixtos; abrir/cerrar caja; crear crédito y dos abonos. Cada paso conserva saldos y movimientos exactos tras reinicio. La factura legal queda deshabilitada hasta verificar sus reglas y campos con fuentes vigentes.
