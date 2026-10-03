# Ferretería: estado y uso en desarrollo

La vertical reutiliza usuarios, permisos, catálogo, inventario, compras, cotizaciones, POS,
devoluciones, caja, crédito y respaldos de Comercial/Core. Usa una base de datos y licencia
independientes de Repuestos.

## Iniciar

```powershell
.\sistemashn.ps1 run -Vertical ferreteria
.\sistemashn.ps1 license -Vertical ferreteria
```

También puede abrirse `SistemasHN.cmd` y elegir **Ferretería** en el menú. Para probar con
datos aislados: `.\scripts\dev.ps1 run -Vertical ferreteria`.

## Flujo operativo

1. Crear una unidad base en Catálogo (pieza, metro, etc.) y el SKU de cada variante que no
   comparta existencias. En su ficha, abrir **Datos de ferretería** para registrar marca,
   familia, especificación y presentaciones.
2. Cada presentación guarda etiqueta, código opcional, factor exacto hacia la unidad base,
   regla de fracción y precio opcional. El factor es inmutable; cambios requieren una nueva
   presentación para conservar el significado histórico.
3. En Nueva compra, Cotizaciones y Punto de venta, introducir el código de presentación o
   elegirla desde el SKU. La pantalla muestra cantidad capturada y su equivalencia en unidad
   base antes de confirmar. El movimiento usa el libro único de inventario comercial.
4. La línea confirmada conserva etiqueta, factor, cantidad original y precio/costo de la
   presentación. Cotización con reserva, conversión a venta y devoluciones usan cantidades
   base para no duplicar existencias. El resumen muestra venta neta sin ISV y margen bruto.

Ejemplo comprobado: comprar 2 cajas de 100 piezas y vender 3 piezas deja 197 piezas.

## Límites actuales

- Un costo por empaque debe convertirse exactamente a 4 decimales por unidad base; un precio
  de venta por empaque, a centavos por unidad base. Se rechazan conversiones que requieran
  redondear sin advertencia.
- El importador Excel existente crea/actualiza productos base; las presentaciones y atributos
  técnicos se gestionan en la ficha del producto.
- El resumen de margen agrupa ventas del período y sus devoluciones vinculadas hasta el fin
  del período. No atribuye al período una devolución de una venta anterior; muestra avisos
  cuando falta costo fiable o vínculo con una venta.
- La factura fiscal sigue deshabilitada hasta completar su validación legal y de producto.
  Esta vertical no incluye varios almacenes ni optimización de cortes.

La opción de compilación selecciona vertical y deja un paquete separado en `build/`;
la verificación de escritorio de esta entrega usa ejecución en desarrollo.
