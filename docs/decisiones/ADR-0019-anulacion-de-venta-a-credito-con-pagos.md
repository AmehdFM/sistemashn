# ADR-0019 — Anulación de venta a crédito con pagos recibidos

- **Estado:** 🔴 **ABIERTA** — requiere definición del negocio
- **Urgencia:** antes de operar crédito en producción
- **Origen:** decisión D-4 y defecto B-8 de [`plan-desarrollo-base-datos.md`](../../plan-desarrollo-base-datos.md)

## Contexto

Una venta a crédito genera una cuenta por cobrar. El cliente abona L. 500 de un
total de L. 2 000. Después la venta se anula.

Preguntas que el sistema no puede responder solo:

- ¿Se cancela la cuenta por cobrar completa?
- ¿Qué pasa con los L. 500 ya cobrados? ¿Se devuelven en efectivo? ¿Se genera
  una nota de crédito? ¿Queda como saldo a favor del cliente para su próxima
  compra?
- ¿Y los pagos ya registrados: se borran, se marcan como revertidos, se dejan
  como están apuntando a una cuenta anulada?

Cada respuesta produce un modelo de datos distinto y un flujo de usuario
distinto.

## Opciones

| Opción | Consecuencia |
|---|---|
| **(a) Devolución en efectivo** | Simple de explicar. Requiere registrar el egreso de caja, que hoy no existe en el modelo |
| **(b) Nota de crédito** | Lo correcto contablemente y probablemente lo que un contador pida. Requiere una entidad nueva y coordinar con [ADR-0020](ADR-0020-procedimiento-de-anulacion-ante-el-sar.md) |
| **(c) Saldo a favor del cliente** | Cómodo para el negocio. Requiere una entidad "cliente" con saldo, que hoy no existe: el sistema no lleva clientes registrados |
| **(d) Prohibir anular una venta a crédito con pagos registrados** | Cero modelo nuevo. El usuario debe resolverlo por otra vía (nota de crédito manual fuera del sistema) |

## Regla provisional vigente

Hasta que se decida, **`sp_AnularVenta` debe rechazar** anular una venta a
crédito que tenga pagos registrados, con un mensaje claro al usuario.

Es deliberadamente restrictivo: es preferible que el sistema diga *"no puedo
hacer esto"* a que deje la contabilidad del cliente en un estado inconsistente
que nadie va a notar hasta el cierre del mes.

Esta regla provisional coincide con la opción **(d)**. Si el negocio la adopta
como definitiva, no hay nada más que implementar — solo cerrar este ADR.

## Nota

Si se elige (c), aparece un requisito que hoy no existe: **el sistema no lleva
clientes registrados**. Las ventas guardan usuario, no cliente. Agregarlos es un
cambio de alcance considerable y debe decidirse aparte.
