# Decisiones de arquitectura (ADR)

Un **ADR** (*Architecture Decision Record*) registra una decisión estructural:
qué se decidió, en qué contexto, qué se descartó y qué consecuencias trae.

**Para qué existe esta carpeta:** para que nadie —persona o IA— vuelva a
discutir una decisión ya tomada, y para que cuando haya que revertirla se sepa
exactamente qué la sostenía.

## Cómo leerlos

- **Aceptada** — está implementada y vigente. No la vuelvas a discutir sin un
  motivo nuevo.
- **Abierta** — 🔴 **requiere definición del negocio.** Ninguna IA la resuelve
  por cuenta propia. Si tu tarea depende de una, decilo y proponé, no asumas.
- **Reemplazada** — quedó atrás; el ADR dice cuál la sustituye.

## Índice

### Aceptadas

| # | Decisión |
|---|---|
| [0001](ADR-0001-core-mas-verticales-en-una-base.md) | Núcleo compartido + verticales sobre una sola base de datos |
| [0002](ADR-0002-logica-de-negocio-en-stored-procedures.md) | Toda la lógica de negocio vive en stored procedures |
| [0003](ADR-0003-dapper-en-vez-de-ef-core.md) | Dapper en vez de Entity Framework Core |
| [0004](ADR-0004-winforms-de-escritorio.md) | Aplicación de escritorio WinForms, no web |
| [0005](ADR-0005-licenciamiento-offline-firmado.md) | Licenciamiento offline con firma RSA atada a la máquina |
| [0006](ADR-0006-registro-de-modulos-por-vertical.md) | Las verticales se enchufan por `IVerticalModuleProvider` |
| [0007](ADR-0007-textos-centralizados-por-capa.md) | Textos centralizados en un `Textos.cs` por capa |
| [0008](ADR-0008-cultura-fija-en-el-arranque.md) | Cultura fija `en-US` en el arranque |
| [0009](ADR-0009-connection-string-en-programdata.md) | Connection string compartido en `ProgramData` |
| [0010](ADR-0010-shell-unico-con-usercontrols.md) | Ventana única con `UserControl`, sin MDI |
| [0011](ADR-0011-iconos-con-segoe-mdl2.md) | Iconografía con la fuente Segoe MDL2 Assets |
| [0012](ADR-0012-bcrypt-verificado-en-la-app.md) | Contraseñas con BCrypt, verificadas en la app |
| [0013](ADR-0013-cantidades-decimales-y-unidades.md) | Cantidades decimales con unidades de medida |
| [0014](ADR-0014-despliegue-por-dacpac.md) | Despliegue y actualización de esquema por DACPAC |
| [0015](ADR-0015-durabilidad-estricta.md) | Durabilidad estricta: `DELAYED_DURABILITY` prohibido |

### Abiertas — 🔴 requieren definición del negocio

| # | Decisión | Urgencia |
|---|---|---|
| [0016](ADR-0016-collation-acento-insensitiva.md) | Collation acento-insensitiva | **Antes de la primera instalación con datos reales** |
| [0017](ADR-0017-estrategia-de-busqueda-de-productos.md) | Estrategia de búsqueda de productos | Al medir con el catálogo del primer cliente |
| [0018](ADR-0018-composicion-historica-de-paquetes.md) | Composición histórica de los paquetes | Antes de vender paquetes en producción |
| [0019](ADR-0019-anulacion-de-venta-a-credito-con-pagos.md) | Anulación de venta a crédito con pagos recibidos | Antes de operar crédito en producción |
| [0020](ADR-0020-procedimiento-de-anulacion-ante-el-sar.md) | Procedimiento formal de anulación ante el SAR | Requiere asesoría contable |
| [0021](ADR-0021-version-minima-de-sql-server.md) | Versión mínima de SQL Server a soportar | Antes de empaquetar el instalador |

## Plantilla para un ADR nuevo

```markdown
# ADR-00XX — <Título en una línea>

- **Estado:** Aceptada | Abierta | Reemplazada por ADR-00YY
- **Fecha:** AAAA-MM-DD

## Contexto
Qué situación obliga a decidir. Las restricciones reales, no las preferencias.

## Decisión
Qué se decidió, en una o dos frases.

## Alternativas descartadas
| Alternativa | Por qué no |

## Consecuencias
Lo bueno y lo malo. Qué queda prohibido o cerrado a partir de acá.
```

**Un ADR se escribe en el mismo commit que el código que lo implementa.** Uno
escrito después es una racionalización, no un registro.
