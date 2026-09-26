# Devoluciones, documentos y reportes: plan de área

**Meta:** corregir operaciones sin borrar historia, entregar comprobantes térmicos/carta y ofrecer reportes básicos confiables. **Depende de:** ventas, compras y caja. **Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.

## Tareas

- [ ] **Anulación.** Servicio que registra motivo, actor, referencia y reversos permitidos sin eliminar factura ni reutilizar número. Definir límites según pagos, caja cerrada y factura legal tras revisar normativa. Probar intento repetido y falta de permiso.
- [ ] **Devolución de cliente.** Cantidad parcial acumulada no supera la vendida; conservar vínculo a línea original, costo y precio aplicados. Clasificar stock vendible o defectuoso/no vendible. Elegir reembolso, cambio o saldo a favor; ajustar deuda/pagos/caja consistentemente. Probar dos devoluciones parciales, defecto, cambio sin stock y reembolso en caja cerrada.
- [ ] **Devolución al proveedor.** Referenciar compra y unidades disponibles/no vendibles; registrar reemplazo, reembolso o crédito futuro, con efecto en stock, costo y cuenta por pagar. Probar devolución parcial y crédito aplicado una sola vez.
- [ ] **Documentos.** Plantillas de cotización, compra, factura genérica/legal y recibo con nombre/logo; PDF guardable y formatos carta y térmico. Capturar datos del documento al emitirlo para que cambios futuros de producto o negocio no alteren el original. Elegir biblioteca/driver tras prueba Windows; probar sin impresora, impresión fallida, texto largo y caracteres españoles.
- [ ] **Excel y reportes.** Exportar listados y ventas/utilidad estimada por período, bajos de stock, saldos por cobrar/pagar y cierres de caja. Calcular utilidad con costo histórico, no con promedio actual; reflejar devoluciones/anulaciones. Consultas paginadas y permisos de costo/finanzas. Probar rango de fechas, filtros vacíos, miles de movimientos y comparación con libro de inventario/caja.
- [ ] **Auditoría y experiencia.** Confirmaciones con resumen económico antes de aplicar; mostrar resultado y documentos relacionados. Simular fallo entre devolución y reembolso y verificar rollback completo.

## Evidencia de salida

Venta con dos líneas, devolución de solo una cantidad defectuosa, saldo a favor y devolución de esa unidad al proveedor; existencias, caja, deuda y utilidad reconciliadas. PDF y pruebas de impresión reales en Windows, Excel abierto con datos correctos y límites legales de factura verificados antes de activarla.
