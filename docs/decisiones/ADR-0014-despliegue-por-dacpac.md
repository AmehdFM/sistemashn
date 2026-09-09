# ADR-0014 — Despliegue y actualización de esquema por DACPAC

- **Estado:** Aceptada *(el mecanismo está elegido; el procedimiento de
  actualización todavía no se ejecutó contra un cliente real)*
- **Fecha:** 2026-09-09

## Contexto

El producto se vende a **muchos clientes, cada uno con su copia**, todos
**offline** y **sin personal técnico en el sitio**. Cuando salga una versión
nueva, hay que actualizar decenas de bases de datos sin que nadie corra scripts
a mano y sin que un error deje al cliente sin poder facturar.

## Decisión

La base de datos se define como **proyectos SSDT (`.sqlproj`)** —
`Sistemas.Core.Database` y `Sistemas.Repuestos.Database` — que compilan a un
**DACPAC**. El despliegue y la actualización comparan el esquema del DACPAC
contra el de la base y aplican solo el diferencial.

Reglas que lo hacen viable:
- **Cada archivo `.sql` define un solo objeto** y vive en la carpeta de su
  esquema y tipo. Todo archivo nuevo se registra en el `.sqlproj`.
- **`Script.PostDeployment.sql` es 100 % idempotente** (`IF NOT EXISTS ... INSERT`).
- **`Configuracion.VersionEsquema`** registra qué versión tiene cada instalación,
  y cada release la incrementa.
- **La app valida al arrancar** que la versión de esquema coincide con la que
  espera, y se niega a operar si no. Un binario nuevo contra un esquema viejo
  corrompe datos en silencio, que es el peor de los fallos posibles.
- **Respaldo completo verificado antes de aplicar**, siempre.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Scripts de migración numerados a mano | Funciona, pero exige disciplina perfecta y no detecta desviaciones: si un cliente tiene el esquema tocado, el script falla o corrompe |
| Migraciones de EF Core | No se usa EF ([ADR-0003](ADR-0003-dapper-en-vez-de-ef-core.md)) |
| Reinstalar la base y recargar datos | Impensable: los datos del cliente son su negocio |

## Consecuencias

**A favor**
- El esquema está versionado en git como código, revisable en un diff.
- La actualización es declarativa: se define el estado deseado, no los pasos.
- El DACPAC detecta y corrige desviaciones del esquema en una instalación tocada.

**En contra — y son importantes**
- **Los `.sqlproj` solo compilan en Windows** con Visual Studio o los SDK de
  SSDT. En Linux o en CI se editan y revisan los `.sql`, no se produce el DACPAC.
- **SSDT no adivina las migraciones de datos.** Renombrar una columna se traduce
  en `DROP` + `ADD`: se pierde el dato. Todo cambio destructivo necesita su
  script de migración escrito a mano.
- **Toda columna nueva `NOT NULL` necesita `DEFAULT`**, o el despliegue falla
  contra una tabla con filas.
- El `DSP` del proyecto fija la versión mínima de SQL Server soportada — ver
  [ADR-0021](ADR-0021-version-minima-de-sql-server.md).
