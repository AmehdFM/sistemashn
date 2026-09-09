# ADR-0020 — Procedimiento formal de anulación ante el SAR

- **Estado:** 🔴 **ABIERTA** — requiere asesoría contable, no criterio técnico
- **Urgencia:** antes de la primera instalación en un cliente que facture con CAI
- **Origen:** decisión D-5 de [`plan-desarrollo-base-datos.md`](../../plan-desarrollo-base-datos.md) §10

## Contexto

El sistema implementa el principio general correcto: **un correlativo emitido no
se reutiliza jamás**. Una factura anulada conserva su número, se marca
`Anulada = 1` y guarda motivo y fecha.

Lo que no está confirmado es cómo debe quedar **formalmente registrada** una
anulación ante el SAR: qué documentación se conserva, si hay que reportar las
anuladas en alguna declaración, qué plazo aplica, y si el manejo difiere según
la factura se anule el mismo día o después de cerrado el período.

## Por qué no se decide desde el diseño

Es materia fiscal, cambia con la normativa vigente, y equivocarse le puede
costar una multa al cliente. **Debe confirmarse con un contador o asesor fiscal
hondureño actualizado**, no deducirse del principio general ni del conocimiento
de un modelo de lenguaje.

## Qué hay que confirmar concretamente

1. ¿Qué debe conservar el contribuyente de una factura anulada? ¿Los ejemplares
   impresos?
2. ¿Hay que reportar las anuladas en alguna declaración periódica?
3. ¿Cambia el procedimiento si la anulación ocurre después del cierre del
   período fiscal?
4. ¿Existe un plazo máximo para anular?
5. ¿El sistema debe imprimir algo al anular, o basta el registro interno?
6. ¿Qué relación tiene esto con la nota de crédito de
   [ADR-0019](ADR-0019-anulacion-de-venta-a-credito-con-pagos.md)?

## Estado actual del código

`Repuestos.Ventas` ya guarda `Anulada`, `MotivoAnulacion` y `FechaAnulacion`, con
un `CHECK` que garantiza que los tres se muevan juntos. Esa base sirve para
cualquiera de los procedimientos posibles.

Lo que puede faltar según la respuesta: un reporte de facturas anuladas por
período, campos adicionales de respaldo documental, o impresión de un
comprobante de anulación.
