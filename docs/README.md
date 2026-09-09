# Documentación de SistemasHN

Esta carpeta contiene el contexto estable del proyecto: qué es, para quién,
cómo está construido y por qué se decidió así. Está escrita tanto para
asistentes de IA como para el desarrollador que vuelva al código dentro de seis
meses.

**El punto de entrada es [`../CLAUDE.md`](../CLAUDE.md)**, no este archivo.

## Índice

| # | Documento | Contenido |
|---|---|---|
| 00 | [Producto y mercado](00-producto-y-mercado.md) | Qué se vende, a quién, cómo se cobra, cómo compite |
| 01 | [Arquitectura](01-arquitectura.md) | Proyectos, capas, dependencias, flujo de arranque, extensibilidad |
| 02 | [Convenciones de código](02-convenciones-codigo.md) | C#, WinForms, Dapper, nombres, errores, comentarios |
| 03 | [Convenciones de base de datos](03-convenciones-base-datos.md) | C-1 a C-9 y las plantillas obligatorias de SQL |
| 04 | [Dominio y glosario](04-dominio-y-glosario.md) | Términos del negocio y mapa de datos |
| 05 | [Estado y roadmap](05-estado-y-roadmap.md) | Qué está terminado, qué es stub, qué sigue |
| 06 | [Despliegue y operación](06-despliegue-y-operacion.md) | Instalación, actualización, respaldo, licencias |
| 07 | [Estrategia de pruebas](07-estrategia-de-pruebas.md) | Verificación hoy y plan de pruebas automatizadas |
| 08 | [Flujo de trabajo con IA](08-flujo-de-trabajo-con-ia.md) | Cómo pedir, cómo entregar, criterios de terminado |
| — | [Decisiones (ADRs)](decisiones/README.md) | El porqué de cada elección estructural |

## Documentos de referencia en la raíz

- [`plan-desarrollo-base-datos.md`](../plan-desarrollo-base-datos.md) — plan de
  construcción de la base de datos con DDL exacto y cuerpos de SP. Es la
  referencia técnica más detallada del proyecto.
- [`GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`](../GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md) —
  guía de diseño visual y de interacción para sistemas empresariales de
  escritorio. Manda sobre toda pantalla nueva.

## Cómo mantener esta documentación

Un documento desactualizado es peor que ninguno, porque la IA lo va a creer.

- **Un cambio estructural exige un ADR.** Si cambia una dependencia entre
  proyectos, un contrato entre capas o una regla que afecta a más de un módulo,
  escribí el ADR en el mismo commit que el código.
- **`05-estado-y-roadmap.md` se actualiza al cerrar cada fase**, no al final.
- **Las convenciones se escriben cuando se rompen, no antes.** Si una revisión
  encuentra un defecto que una regla escrita habría evitado, la regla se agrega
  a `02` o `03` en ese mismo momento.
- **Nada de "próximamente".** Si algo no existe, este repositorio lo dice con
  todas sus letras y en `05-estado-y-roadmap.md`.
