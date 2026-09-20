# Programa de mejora UI/UX

Este directorio convierte la guía visual general del repositorio en una
especificación aplicable al estado actual de SistemasHN y, después de su
aprobación, en un plan de trabajo ejecutable por otro agente.

## Estado de los documentos

| Documento | Estado | Propósito |
|---|---|---|
| [`00-diagnostico-actual.md`](00-diagnostico-actual.md) | Listo para revisión | Inventario del estado actual, fortalezas, inconsistencias y riesgos. |
| [`01-especificacion-sistema-diseno.md`](01-especificacion-sistema-diseno.md) | Listo para revisión | Contrato visual y de interacción que deberá cumplir Core y cada vertical. |
| [`02-arquitectura-navegacion.md`](02-arquitectura-navegacion.md) | Listo para revisión | Estructura de acceso, orden del sidebar, comportamiento del shell e iconografía. |
| [`03-plan-desarrollo-ui-ux.md`](03-plan-desarrollo-ui-ux.md) | Listo para ejecución | Secuencia de implementación detallada para Terra o Luna. |
| [`04-matriz-migracion-pantallas.md`](04-matriz-migracion-pantallas.md) | Listo para ejecución | Matriz pantalla por pantalla con criterios de aceptación. |
| [`05-checklist-qa-visual.md`](05-checklist-qa-visual.md) | Listo para ejecución | Guion de validación visual, DPI, teclado y estados. |

## Orden de autoridad

Estos documentos no sustituyen la arquitectura ni las reglas existentes. El
orden aplicable sigue siendo:

1. `CLAUDE.md` y sus reglas duras.
2. ADRs de `docs/decisiones/`.
3. `GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`.
4. La especificación de este directorio, que adapta la guía al código real.
5. El plan de desarrollo y la matriz de migración.
6. El código existente cuando no contradiga una decisión documentada.

Si aparece una contradicción, no se resuelve silenciosamente. Se registra y se
actualiza el documento que haya quedado desfasado.

## Línea base

La línea base es el árbol de trabajo existente el 20 de septiembre de 2026,
incluidos los cambios todavía sin commit. No se propone regresar a un commit
anterior ni descartar el rediseño ya realizado.

## Estado de ejecución

Las tareas 1 a 11 están registradas como **Migradas** en la matriz. La tarea
12 conserva evidencia estática, pero requiere pruebas visuales reales. No hay
pantallas **Conformes** mientras no se complete la checklist en los DPI y
resoluciones definidos; las deudas y pruebas pendientes viven en la matriz.

## Resultado esperado

Al terminar el programa, una pantalla nueva debe poder construirse combinando
componentes de `Sistemas.Core.UI` sin volver a decidir:

- paleta, fuentes, alturas, espaciado o anchos semánticos;
- anatomía de encabezado, toolbar, filtros, contenido y pie;
- orden y jerarquía de botones;
- estilo, alineación y estados de tablas;
- presentación de carga, vacío, error y éxito;
- comportamiento de ayudas contextuales;
- navegación por teclado, foco inicial y atajos;
- respuesta ante DPI y resoluciones soportadas.

La consistencia debe surgir de componentes compartidos y contratos verificables,
no de que cada desarrollador recuerde una guía extensa.
