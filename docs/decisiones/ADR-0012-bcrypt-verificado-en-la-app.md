# ADR-0012 — Contraseñas con BCrypt, verificadas en la app

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

[ADR-0002](ADR-0002-logica-de-negocio-en-stored-procedures.md) manda que toda
regla de negocio viva en el SP. La verificación de contraseña es la excepción, y
merece justificarse.

SQL Server no tiene una función de hash con costo ajustable. `HASHBYTES` calcula
SHA-256, que está diseñado para ser **rápido** — justo lo contrario de lo que
hace falta contra un ataque de fuerza bruta sobre un archivo de base robado.
Tampoco maneja salt por sí solo.

## Decisión

**BCrypt (`BCrypt.Net-Next`) en la capa de C#**, con esta división:

- **La base guarda y entrega el hash**, nunca la contraseña. `sp_CrearUsuario`
  recibe un `PasswordHash` ya calculado; `sp_ObtenerCredencialesLogin` devuelve
  el hash almacenado.
- **La app calcula y compara** con `BCrypt.Verify(password, hash)`.
- **La base registra el resultado.** `sp_RegistrarResultadoLogin` se llama
  siempre, con éxito o fracaso, para llevar el conteo de intentos y la auditoría.

Al usuario se le devuelve siempre el mismo mensaje genérico —
`Usuario o contraseña incorrectos` — para no revelar si el usuario existe.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `HASHBYTES('SHA2_256', ...)` en SQL | Rápido por diseño: millones de intentos por segundo contra una base robada. Sin salt ni costo ajustable |
| Ensamblado CLR en SQL Server con BCrypt | Habilitar CLR en la instancia del cliente agrega superficie de ataque y complica la instalación |
| Autenticación de Windows para los usuarios de la app | El negocio tiene un solo usuario de Windows compartido entre los empleados. Los usuarios de la app son otra cosa |

## Consecuencias

**A favor**
- Costo ajustable y salt por hash, gratis.
- La contraseña en claro nunca viaja al servidor de base de datos.
- Es la excepción más justificable a ADR-0002: no es una regla de negocio, es
  una primitiva criptográfica que el motor no ofrece.

**En contra**
- Una excepción documentada a "todo en el SP" que hay que conocer para no
  "corregirla".
- Quien se conecte por SSMS podría insertar un usuario con un hash arbitrario —
  pero para eso ya necesitaría acceso administrativo a la base, escenario en el
  que la contraseña de la app es el menor de los problemas.
- **`UsuarioId` no se deduce en SQL**: la conexión usa autenticación integrada de
  Windows y todos los usuarios de la app comparten el mismo login de SQL Server.
  Por eso cada SP auditable recibe `@UsuarioId` como parámetro explícito.
