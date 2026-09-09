# ADR-0018 — Composición histórica de los paquetes

- **Estado:** 🔴 **ABIERTA** — requiere definición del negocio
- **Urgencia:** antes de vender paquetes en producción
- **Origen:** decisión D-3 y defecto B-7 de [`plan-desarrollo-base-datos.md`](../../plan-desarrollo-base-datos.md)

## Contexto

Un **paquete** es un producto compuesto: un kit de frenos que se vende como una
línea pero descuenta el stock de sus componentes. Su composición vive en
`Repuestos.PaqueteDetalle`.

El problema: si el paquete se **rearma** después de haberse vendido —se le
cambia un componente, se le agrega otro— y luego se **anula** aquella venta, la
anulación devuelve al stock los componentes **actuales**, no los que realmente
salieron de la bodega.

El resultado es inventario que no cuadra, y de la peor forma: en silencio, sin
error, descubierto meses después en un conteo físico.

## Opciones

| Opción | Consecuencia |
|---|---|
| **(a) Guardar en `VentaDetalle` las líneas expandidas** además de la línea comercial del paquete | Corrección total: la venta registra exactamente qué salió. Costo: más filas por venta y una consulta más compleja para mostrar la factura como el usuario la espera |
| **(b) Versionar `PaqueteDetalle` con vigencia** | Corrección total sin inflar `VentaDetalle`. Costo: el modelo se complica bastante y toda consulta de composición pasa a necesitar la fecha |
| **(c) Prohibir rearmar un paquete que ya tiene ventas** y obligar a crear uno nuevo | La más simple, la más barata de implementar y la más fácil de explicarle al usuario: *"este kit ya se vendió, creá uno nuevo"* |

**Recomendación: (c).** No cuesta modelo ni consultas, y el flujo que impone es
razonable para el negocio: un kit que cambia de contenido, en la práctica, es
otro kit.

## Por qué no se decide sobre la marcha

Es una regla de negocio, no una elección técnica. Determina qué puede hacer el
usuario con un paquete ya vendido, y las tres opciones producen sistemas que se
usan distinto.

## Estado actual del código

El sistema **no implementa ninguna de las tres**. Hasta que se decida, armar un
paquete que ya tiene ventas produce el descuadre descrito. Si se elige (c), la
validación va en `sp_ArmarPaquete`: rechazar si existe una venta que incluya ese
paquete.
