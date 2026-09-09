# ADR-0015 — Durabilidad estricta: `DELAYED_DURABILITY` prohibido

- **Estado:** Aceptada
- **Fecha:** 2026-09-09

## Contexto

En el mercado objetivo **los cortes de energía son rutina**, no una anomalía. La
PC del cliente rara vez tiene UPS. La pregunta no es si se va a cortar la luz en
medio de una venta, sino cuántas veces por mes.

SQL Server ofrece `DELAYED_DURABILITY`, que confirma la transacción antes de
escribir el log en disco. Mejora el rendimiento de escritura de forma notable, y
es una tentación real en hardware lento con disco mecánico.

Lo que cuesta: ante una caída, **se pierden transacciones que el sistema ya
confirmó**. Es decir, el cliente ve "Factura emitida", se va la luz, y al volver
la factura no existe — pero el correlativo sí se consumió y el producto salió de
la tienda.

## Decisión

**`DELAYED_DURABILITY` está prohibido en cualquier forma** — a nivel de base, de
transacción o de procedimiento. La durabilidad es innegociable.

Reglas que lo acompañan:
- **Toda operación de dinero o inventario es una sola transacción atómica.** Se
  completa entera o no ocurrió.
- **`SYSDATETIME()` siempre**, nunca `GETUTCDATE()`: no hay red ni nada con qué
  sincronizar, y el reloj de la máquina es la única referencia.
- **El respaldo automático es parte del producto**, no una comodidad. Ver
  [`../06-despliegue-y-operacion.md`](../06-despliegue-y-operacion.md) §4.
- **`DBCC CHECKDB` periódico**: un corte puede corromper páginas, y sin revisión
  eso se descubre meses después.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `DELAYED_DURABILITY = FORCED` para ganar rendimiento | Cambia rendimiento por perder transacciones confirmadas ante un corte — exactamente el escenario que hay que evitar |
| Activarlo solo en operaciones "no críticas" | La auditoría también importa, y la complejidad de mantener dos regímenes de durabilidad garantiza que alguien se equivoque de lado |
| Exigir UPS al cliente | No se puede controlar, y el producto tiene que sobrevivir a que no lo tenga |

## Consecuencias

**A favor**
- Lo que el sistema dice que guardó, está guardado.
- El modelo mental es simple: la operación ocurrió o no ocurrió.

**En contra**
- Se renuncia a una mejora de escritura real en discos lentos. Se compensa por
  el lado correcto: transacciones cortas (C-6: validar antes de abrir),
  operaciones por conjunto (C-7) e índices que cubren la consulta.
- Cada transacción paga su escritura de log. En un disco mecánico se nota, y es
  el precio correcto a pagar.
