# ADR-0016 — Collation acento-insensitiva

- **Estado:** 🔴 **ABIERTA** — requiere definición del negocio
- **Urgencia:** **Antes de la primera instalación con datos reales.** Es la
  decisión más costosa de revertir de todo el proyecto.
- **Origen:** decisión D-1 de [`plan-desarrollo-base-datos.md`](../../plan-desarrollo-base-datos.md) §10

## Contexto

El `.sqlproj` declara hoy `ModelCollation` = **`1033, CI`**: *case-insensitive*
pero **acento-sensitiva**.

En una tienda de repuestos, el vendedor teclea rápido y sin tildes con un
cliente esperando en el mostrador. Con la collation actual:

- `bujia` **no encuentra** `bujía`
- `cigueñal` **no encuentra** `cigüeñal`
- `direccion` **no encuentra** `dirección`

El resultado que ve el cliente: *"el sistema dice que no hay"* sobre producto
que está en bodega. Se pierde la venta y se pierde la confianza en el sistema.

## Opciones

| Opción | Consecuencia |
|---|---|
| **(a) Cambiar a `Modern_Spanish_CI_AI`** | Búsqueda acento-insensitiva y con ordenamiento correcto del español (la `ñ` después de la `n`). Es la opción técnicamente más correcta para el idioma |
| **(b) Cambiar a `Latin1_General_CI_AI`** | Acento-insensitiva también, más común y con menos sorpresas de interoperabilidad, pero sin las reglas específicas del español |
| **(c) Dejarla como está** | Se convive con el problema y se compensa normalizando el texto en la app antes de buscar — más código y más superficie de error, en todos los puntos de búsqueda |

**Recomendación técnica: (a)**, salvo que aparezca un motivo concreto de
interoperabilidad que empuje a (b).

## Por qué no se decide sobre la marcha

Cambiar la collation con datos ya cargados **no es un `ALTER`: es una migración
completa** — hay que recrear cada columna de texto, cada índice y cada
restricción que dependa de ella. Con un cliente operando, eso es una ventana de
downtime y un riesgo de pérdida de datos que no vale la pena correr.

**Debe resolverse antes de crear la primera base con datos reales.**

## Cómo implementarla cuando se decida

1. Cambiar `ModelCollation` en **ambos** `.sqlproj` (Core y la vertical). Si
   difieren, cualquier `JOIN` entre esquemas falla con error de collation.
2. Reconstruir la base de desarrollo desde cero.
3. Verificar la búsqueda con tildes y sin tildes en el catálogo de prueba.
4. Verificar que `UQ_Productos_Codigo` siga comportándose como se espera: con
   `CI_AI`, `BUJIA` y `bujía` pasan a ser el **mismo** código, lo que puede ser
   deseable o no. **Este punto hay que decidirlo junto con el principal.**
