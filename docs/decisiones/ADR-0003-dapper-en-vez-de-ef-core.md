# ADR-0003 — Dapper en vez de Entity Framework Core

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

Toda la lógica está en stored procedures ([ADR-0002](ADR-0002-logica-de-negocio-en-stored-procedures.md)),
así que lo único que hace falta del lado de C# es **mapear un result set a un
DTO**. Además, el sistema corre en SQL Server Express con 1 GB de buffer pool
sobre una PC de bajos recursos: el SQL que llega al servidor tiene que ser el
que uno escribió, no el que un generador decidió.

## Decisión

**Dapper** como único micro-ORM. Cada método de servicio abre su conexión con
`ConnectionFactory`, llama al SP con `commandType: CommandType.StoredProcedure`,
y mapea el resultado a un DTO o a una tupla con nombres.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Entity Framework Core | Genera el SQL, mantiene un change tracker y una caché que no necesitamos, y agrega arranque frío y memoria en una máquina que no los tiene. Con toda la lógica en SPs, EF sería un envoltorio caro sobre `ExecuteStoredProcedure` |
| ADO.NET puro | Es lo que hace Dapper, pero escribiendo a mano el mapeo de cada columna en cada método. Más código y más superficie de error por cero beneficio |

## Consecuencias

**A favor**
- El SQL que corre es exactamente el que está en el `.sqlproj`, revisable.
- Superficie mínima: `QueryAsync`, `QueryFirstAsync`, `QueryMultipleAsync`,
  `ExecuteAsync`, `ExecuteScalarAsync`.
- Arranque rápido y memoria baja.

**En contra**
- No hay migraciones automáticas; el esquema se maneja con SSDT
  ([ADR-0014](ADR-0014-despliegue-por-dacpac.md)).
- El mapeo es por convención de nombres: si una columna del SP cambia de nombre
  y el DTO no, la propiedad llega en `default` **sin ningún error**. Es la
  trampa más común de este stack.
- Las columnas nulas exigen `CAST(NULL AS <tipo>)` en el SP (C-4), o Dapper
  revienta al mapear.
