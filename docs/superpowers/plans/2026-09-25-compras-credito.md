# Compras, proveedores y crédito: plan de área

**Meta:** recibir mercadería al contado o crédito, preservar precios de proveedor y controlar cuentas por pagar con pagos parciales. **Depende de:** catálogo/inventario. **Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.

## Datos y reglas

Una contraparte comercial puede actuar como proveedor y cliente sin crear identidades inconsistentes. La compra confirmada conserva encabezado, líneas, cantidades, precio/costo del momento, proveedor, movimientos y auditoría. El pago inicial puede ser mixto; el saldo pendiente produce una cuenta por pagar con vencimiento. Los abonos son hechos históricos separados, nunca una sobreescritura del importe original.

## Tareas

- [ ] **Contrapartes.** Identidad comercial, contactos mínimos y roles proveedor/cliente; búsqueda paginada y deduplicación asistida. Probar nombre coincidente sin fusionar personas distintas y un proveedor que luego se vuelve cliente.
- [ ] **Compra.** Servicio transaccional que valida líneas, cantidades y permisos, registra ingreso y recalcula costo promedio. Capturar costo/precio histórico por proveedor. Prueba de varias líneas con fallo al final: ni stock, ni deuda, ni auditoría comercial parciales.
- [ ] **Cuentas por pagar.** Crear obligación por diferencia entre total y pagos confirmados; fecha de vencimiento, saldo y estado derivado. Abonos parciales en efectivo/tarjeta/transferencia; no exceden saldo. Probar importe cero/negativo, duplicación por reintento, vencimiento y compra totalmente pagada.
- [ ] **Consulta.** Historial por proveedor, precio anterior de pieza y saldos pagados/pendientes, con permisos separados para ver costos y registrar pagos. Exportar información según plan de documentos; no exponer costo a un perfil sin permiso.
- [ ] **Recepción/errores.** Confirmación explícita antes de mover inventario; error de base bloqueada con reintento limitado y mensaje sin duplicar compra. Ensayar recuperación después de cierre abrupto.

## Evidencia de salida

Flujo completo de compra con dos productos y costo promedio comprobado, compra a crédito con dos abonos y saldo exacto, historial intacto tras cambio de precio de proveedor, rollback probado y permisos verificados en UI/servicio.
