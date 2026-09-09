# ADR-0001 — Núcleo compartido + verticales sobre una sola base de datos

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El producto se vende a rubros distintos —autorepuestos primero, ferretería
después— que comparten el 70 % de las necesidades (usuarios, catálogo,
facturación CAI, auditoría, configuración) y difieren en el resto. Reescribir
ese 70 % por cada rubro es insostenible para un desarrollador solo.

Al mismo tiempo, cada cliente tiene **su propia instalación y su propia base**:
no hay multi-tenancy que resolver.

## Decisión

Un **núcleo compartido** (`Sistemas.Core`, `Sistemas.Core.UI`,
`Sistemas.Core.Database`) más una **vertical por rubro**, todo dentro de **una
sola base de datos** separada por esquemas de SQL Server.

Dos reglas lo sostienen:
- **Core nunca conoce una vertical.** Sin referencias, sin `if` por rubro, sin
  tipos de una vertical en Core. La extensión pasa por
  [ADR-0006](ADR-0006-registro-de-modulos-por-vertical.md).
- **La vertical nunca modifica Core** (convención C-2). La referencia por FK y
  nada más: ni un `ALTER TABLE` sobre `Inventario.Productos`.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Un producto monolítico por rubro | Duplica el núcleo y multiplica por N el costo de cada corrección |
| Una base de datos por vertical en la misma instancia | Express tiene tope de 10 GB **por base**, pero las FK entre bases no existen y las transacciones distribuidas en Express son una pesadilla operativa |
| Plugins cargados por reflexión en runtime | Complejidad de carga y versionado que no compra nada: el ejecutable ya se compila por vertical |

## Consecuencias

**A favor**
- Una corrección en Core beneficia a todas las verticales.
- Una vertical nueva es cuatro proyectos y una línea cambiada en `Program.cs`.
- FK reales entre el catálogo de Core y las tablas de la vertical, con
  integridad garantizada por el motor.

**En contra**
- Core carga con la disciplina de no filtrar nada específico de un rubro. Cada
  vez que algo "casi general" quiere subir, hay que decidir con criterio.
- Todas las verticales de una máquina comparten base y connection string
  ([ADR-0009](ADR-0009-connection-string-en-programdata.md)).

**Prueba de fuego:** construir la vertical de ferretería. Si obliga a tocar
Core, la abstracción falló y hay que arreglarla en Core, no parchear la vertical.
