# ADR-0008 — Cultura fija `en-US` en el arranque

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El formato de números depende de la configuración regional de cada Windows, y
en las máquinas de los clientes esa configuración es impredecible: algunas
vienen con `es-ES` (coma decimal), otras con `en-US` (punto decimal), otras
mal configuradas de fábrica.

Si el formato varía por máquina, el mismo precio se ve distinto en dos
terminales del mismo negocio, y una cantidad tecleada puede interpretarse como
mil veces su valor. En un sistema de facturación eso es inaceptable.

La convención hondureña coincide con `en-US`: **punto decimal y coma de miles**.

## Decisión

`Program.cs` fija la cultura antes de cualquier otra cosa:

```csharp
var cultura = CultureInfo.GetCultureInfo("en-US");
CultureInfo.DefaultThreadCurrentCulture = cultura;
CultureInfo.DefaultThreadCurrentUICulture = cultura;
```

Dos detalles que **no** son negociables:

- Se usa **`DefaultThreadCurrentCulture`**, no solo `CurrentThread.CurrentCulture`.
  Las continuaciones `async` y los hilos del threadpool (los que usa Dapper)
  no heredan la del hilo actual: heredan la default. Sin esto, el formato
  cambiaría según en qué hilo se resolviera la operación.
- El dinero se formatea con **`"N2"`** y los conteos con `"N0"`. **Nunca `"C"`**:
  el formato de moneda de `en-US` traería `$`. El símbolo `L. ` se antepone a
  mano.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Usar la cultura del sistema | Es exactamente el problema |
| Crear una `CultureInfo` personalizada "es-HN" | .NET no trae `es-HN` con los formatos deseados en todas las plataformas, y construir una cultura a mano agrega superficie de fallo por cero beneficio: `en-US` ya tiene el formato correcto |
| Formatear todo con `InvariantCulture` en cada llamada | Depende de recordarlo en cada punto del código. Un olvido produce un número mal formateado en una factura |

## Consecuencias

**A favor**
- Idéntico comportamiento numérico en cualquier Windows del cliente.
- El parseo de lo que el usuario teclea es predecible.

**En contra**
- El nombre `en-US` es engañoso para quien lea el código sin el comentario. Por
  eso `Program.cs` lleva el comentario que lo explica y no debe borrarse.
- Los nombres de meses y días que .NET produzca vendrán en inglés. Hoy no se
  muestran; si algún día se necesitan, hay que formatearlos aparte.
