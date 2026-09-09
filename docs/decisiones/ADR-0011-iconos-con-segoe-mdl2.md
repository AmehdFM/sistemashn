# ADR-0011 — Iconografía con la fuente Segoe MDL2 Assets

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El sidebar y los botones necesitan iconos. Empaquetar imágenes `.png` implica
producirlas, versionarlas, exportarlas en varias resoluciones para distintos DPI
y mantenerlas consistentes entre módulos y verticales — un trabajo de diseño
recurrente que un desarrollador solo no va a sostener.

## Decisión

Los iconos son **un solo carácter de la fuente "Segoe MDL2 Assets"**, que viene
instalada con Windows. Está en el contrato: `IDashboardModule.Glyph` es un
`string` de un carácter, y `UiTheme.FuenteGlyph` define la fuente y su tamaño.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Imágenes `.png` embebidas | Trabajo de diseño recurrente, varias resoluciones por DPI, y peso en el ensamblado |
| Iconos SVG | WinForms no los renderiza sin una librería extra, y eso choca con la regla R4 de no agregar dependencias |
| Una fuente de iconos de terceros (Font Awesome y similares) | Habría que empaquetarla y registrarla en runtime; MDL2 ya está en toda máquina Windows moderna |

## Consecuencias

**A favor**
- Cero archivos de imagen que mantener.
- Escala perfecto en cualquier DPI, porque es texto.
- Cambiar un icono es cambiar un carácter.
- Se colorea con `ForeColor`, así que respeta el tema automáticamente.

**En contra**
- Atado a Windows, lo cual ya es un hecho por [ADR-0004](ADR-0004-winforms-de-escritorio.md).
- El catálogo de glifos disponibles limita la elección: a veces no hay un icono
  exacto para el concepto y hay que conformarse con el más cercano.
- Los códigos de glifo son opacos al leer el código; conviene comentar cuál es.
- Se debe verificar que la fuente exista en la versión mínima de Windows que se
  soporte.
