# ADR-0007 — Textos centralizados en un `Textos.cs` por capa

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El sistema le habla al usuario en español todo el tiempo: mensajes de error,
confirmaciones, rótulos. Con los literales repartidos por las pantallas pasan
tres cosas: se dice lo mismo de tres formas distintas, corregir una palabra
obliga a buscar por todo el código, y aparecen mensajes técnicos sin filtrar
delante de un usuario que no tiene a quién preguntarle.

Además, la marca blanca exige que el tono sea consistente: el cliente ve su
logo, así que el sistema tiene que sonar como un solo producto.

## Decisión

**Ningún string visible para el usuario fuera de un `Textos.cs`.** Tres
archivos, con alcance estricto, siguiendo la misma frontera que
[ADR-0001](ADR-0001-core-mas-verticales-en-una-base.md):

| Archivo | Alcance |
|---|---|
| `Sistemas.Core/Textos.cs` | Capa de negocio compartida: auth, licencia, Excel |
| `Sistemas.Core.UI/Textos.cs` | Pantallas compartidas: arranque, dashboard, ajustes, comunes |
| `Sistemas.Repuestos.Library/Textos.cs` | Todo lo de esa vertical |

Se organizan en clases anidadas por área (`Textos.Comun`, `Textos.Auth`,
`Textos.Dashboard`) con `const string`. Los mensajes con datos variables usan
placeholders `{0}` y `string.Format`, no concatenación.

La regla hermana: **ningún color ni fuente fuera de `UiTheme`**, por el mismo
motivo.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Archivos `.resx` | Es la herramienta de .NET para localización a varios idiomas. Acá hay un solo idioma para siempre; los `.resx` agregarían indirección y un editor incómodo sin comprar nada |
| Literales en cada pantalla | El problema que se está resolviendo |
| Un único `Textos.cs` global | Obligaría a que Core conociera los textos de cada vertical, rompiendo ADR-0001 |

## Consecuencias

**A favor**
- Corregir una palabra en todo el sistema es un solo cambio.
- Se puede auditar de un vistazo todo lo que el sistema le dice al usuario.
- Escribir un mensaje obliga a mirar los vecinos, y eso empuja a la consistencia.

**En contra**
- Un salto más para leer una pantalla.
- Nada del compilador impide escribir un literal suelto: es disciplina, y por
  eso está como regla dura R3 en `CLAUDE.md` y en la checklist de terminado.
- Si algún día hiciera falta un segundo idioma, habría que migrar a `.resx`.
  Con el mercado objetivo, es un riesgo que se acepta.
