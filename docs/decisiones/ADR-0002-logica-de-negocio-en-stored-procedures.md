# ADR-0002 — Toda la lógica de negocio vive en stored procedures

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El sistema maneja dinero e inventario en un entorno donde:
- No hay personal técnico que detecte una inconsistencia a tiempo.
- El dueño del negocio a veces sabe lo suficiente para abrir SSMS.
- La capa de UI es la parte del sistema con más probabilidad de ser reescrita.
- Puede haber dos terminales operando la misma caja al mismo tiempo.

Si la regla de negocio vive en C#, cualquiera de esas cuatro cosas la elude.

## Decisión

**Toda regla de negocio vive en el stored procedure** (convención C-3). La capa
de C# orquesta, presenta y mapea, pero no decide. Un SP debe ser correcto aunque
lo llamen a mano desde SSMS.

Corolarios obligatorios:
- **C-4:** contrato de salida uniforme `Exito` / `Mensaje` + columnas propias.
- **C-5:** plantilla de transacción con soporte de anidamiento.
- **C-6:** validar antes de abrir la transacción.

**Excepciones documentadas, y son solo dos:**
1. La verificación de contraseña con BCrypt ocurre en C#
   ([ADR-0012](ADR-0012-bcrypt-verificado-en-la-app.md)).
2. Consultas triviales de solo lectura sin regla de negocio pueden ir en SQL
   literal dentro del servicio (por ejemplo `SELECT COUNT(1) FROM Security.Usuarios`).
   Si filtran por algo que viene del usuario, van a SP.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Lógica en la capa de servicios de C# | Se elude conectándose por fuera. Y la validación de stock sin bloqueo en la base es una condición de carrera garantizada entre dos cajas |
| ORM con reglas en entidades de dominio | Mismo problema, más capas, y el ORM decide el SQL — inaceptable en Express con 1 GB de buffer pool |
| Triggers | Lógica invisible que se dispara sola. Imposible de depurar por teléfono con un cliente |

## Consecuencias

**A favor**
- La integridad no depende de qué cliente se conecte.
- Las operaciones de dinero son transacciones atómicas de una sola ida al servidor.
- Los mensajes al usuario nacen en español donde se toma la decisión.

**En contra**
- La lógica está en un lenguaje sin pruebas unitarias fáciles ni refactor
  automático. Se compensa con la disciplina de las plantillas y con las pruebas
  de integración de nivel 1 de [`../07-estrategia-de-pruebas.md`](../07-estrategia-de-pruebas.md).
- Un cambio de regla toca SQL y C# a la vez.
- Requiere que quien programe sepa T-SQL de verdad: transacciones, bloqueos,
  `XACT_STATE()`.
