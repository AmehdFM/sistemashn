# UI/UX de escritorio Windows aplicada a SistemasHN

Revisión: 2026-09-30. Alcance: aplicación Flet 1.0 para Repuestos, con pantalla objetivo de 1366×768, mouse y teclado. Se conservan la paleta Grafito y Vino y las decisiones funcionales de `docs/superpowers/plans/ui-ux-investigacion.md`.

## Hallazgos y decisiones

| Tema | Evidencia | Aplicación en SistemasHN |
|---|---|---|
| Navegación | Microsoft recomienda destinos estables, etiquetas claras y jerarquía poco profunda ([Navigation basics](https://learn.microsoft.com/en-us/windows/apps/design/basics/navigation-basics)). | Barra lateral por grupos y ruta activa visible. Los destinos avanzados siguen separados del trabajo diario. |
| Jerarquía tipográfica | Windows usa cuerpo 14/20, subtítulo 20/28 y título 28/36 en píxeles efectivos ([Typography](https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/typography)). | Fuente Segoe UI, cuerpo 14, encabezado de pantalla 28, subtítulos 20 y texto auxiliar 12. Segoe UI funciona también en Windows 10. |
| Distribución | Microsoft agrupa controles con separaciones consistentes de 8 y 12 px y títulos ligados al contenido ([Content layout and spacing](https://learn.microsoft.com/en-us/windows/apps/design/style/spacing)). | Escala 4/8/12/16/24/32, márgenes de 24 px y encabezado con título, explicación y acciones. |
| Densidad empresarial | En aplicaciones de trabajo, primero se mejora agrupación, búsqueda y adaptación; no se compactan todos los controles a la vez ([Design for productivity](https://learn.microsoft.com/en-us/windows/apps/get-started/line-of-business/design-for-lob)). | POS conserva espacio para cobrar; tablas administrativas usan filas legibles y desplazamiento horizontal cuando haga falta. |
| Formularios | Las etiquetas deben identificar los campos y los grupos; el número de columnas depende del ancho ([Forms](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/forms)). | Campos con etiqueta visible, tamaño de texto uniforme y formularios verticales en inicio/configuración. |
| Accesibilidad | Contraste de texto de al menos 4.5:1 y comprobación con escalado de texto ([Accessible text requirements](https://learn.microsoft.com/en-us/windows/apps/design/accessibility/accessible-text-requirements)); controles y contenedores deben poder crecer ([Text scaling](https://learn.microsoft.com/en-us/windows/apps/develop/input/text-scaling)). | Se oscurece el texto secundario sobre blanco, se evitan alturas fijas en contenido y se conservan foco y controles estándar de Flet. |
| Diálogos | Reservar interrupciones modales para decisiones relevantes ([Dialogs and flyouts](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/dialogs-and-flyouts/)). | Mantener confirmaciones de operaciones críticas; los estados ordinarios siguen en la pantalla. |

Estas pautas son de WinUI; SistemasHN usa Flet. Se trasladan **criterios visuales y de interacción**, no componentes o API de WinUI. Las medidas se comprobarán en Flet 1.0 y en la ventana real de Windows.

## Aplicación transversal

1. Definir una escala tipográfica en `core/ui/theme.py` para texto sin tamaño explícito en todas las pantallas.
2. Unificar encabezados, texto auxiliar y tablas en `core/ui/widgets.py`.
3. Ajustar el cascarón y las pantallas de inicio para márgenes, navegación y títulos coherentes.
4. Pasar las tablas construidas directamente por las pantallas al estilo común.

La prueba visual en Windows se realizó con la ventana de desarrollo a 1264×710: inicio de sesión, Usuarios, Catálogo y Punto de venta. Se verificaron la legibilidad de textos y controles, el contraste, la navegación lateral y la distribución de acciones. Queda pendiente una comprobación visual específica con escalado de texto de Windows al 150–200 % y de los flujos con datos abundantes. Las pruebas automatizadas verifican la estructura de controles, pero no sustituyen esa inspección visual.
