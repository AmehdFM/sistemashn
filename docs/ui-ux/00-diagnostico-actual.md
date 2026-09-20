# Diagnóstico UI/UX del estado actual

**Fecha de revisión:** 2026-09-20  
**Línea base:** árbol de trabajo actual, incluidos cambios sin commit  
**Alcance:** `Sistemas.Core.UI`, pantallas de `Sistemas.Repuestos.Library` y
composición del ejecutable `Sistemas.Repuestos`

## 1. Resumen ejecutivo

SistemasHN ya tiene una dirección visual coherente y una base compartida mejor
que la de un proyecto WinForms típico. La paleta "Grafito y Vino", la rejilla
de 4/8 px, `GridStyler`, `Botones`, `FormularioLayout`, `EstadoListaControl` y
`PaginacionControl` demuestran que el rediseño no empieza desde cero.

El problema principal es que el sistema de diseño todavía es **orientativo** en
varias áreas. Las pantallas pueden saltarse los componentes compartidos,
inventar tamaños o fuentes, mezclar jerarquías de botones y construir estados
de forma diferente. El resultado depende demasiado de decisiones locales.

La mejora debe convertir esa base en un contrato completo:

1. tokens con nombres de rol y métricas semánticas;
2. componentes compartidos para los patrones repetidos;
3. cinco arquetipos de pantalla aplicados de manera consistente;
4. navegación organizada por trabajo real del usuario;
5. una migración incremental con criterios de aceptación medibles.

## 2. Restricciones que gobiernan el rediseño

- WinForms sobre .NET 10 se conserva.
- El producto funciona 100 % offline.
- No se agregan dependencias sin autorización.
- Core nunca referencia una vertical.
- Las verticales registran módulos mediante `IVerticalModuleProvider` e
  `IDashboardModule`.
- Todo texto visible vive en el `Textos.cs` de su capa.
- Todo color y fuente vive en `UiTheme`.
- El producto debe operar en equipos modestos y resoluciones limitadas.
- La captura frecuente debe poder hacerse con teclado.
- No hay automatización de UI; la validación visual será manual y reproducible.

## 3. Inventario de superficies

### 3.1 Shell y navegación

| Superficie | Responsabilidad actual | Observación |
|---|---|---|
| `FormDashboardBase` | Sidebar, contenido, usuario y cierre de sesión | La base es correcta; mezcla construcción del shell, navegación, ciclo de vida y presentación de sesión. |
| `SidebarItem` | Ícono, texto, hover y activo | No existe grupo, separador, tooltip colapsado ni estado deshabilitado. |
| `MenuDashboardModule` | Entrada inicial "Menú" | Duplica el acceso del sidebar sin aportar resumen operativo. |
| `ModuleLauncherControl` | Cuadrícula de accesos grandes | Es un lanzador, no un tablero; carece de encabezado, jerarquía por frecuencia y contexto de negocio. |
| `DashboardModuleRegistry` | Registro y orden global | El entero `Orden` permite ordenar, pero no agrupar ni ubicar acciones utilitarias al pie. |

### 3.2 Arranque y acceso

- `FormArranque`
- `ActivacionStepControl`
- `PrimerUsuarioStepControl`
- `DatosNegocioStepControl`
- `LoginStepControl`

Los pasos ya fueron migrados parcialmente a layouts flexibles. Falta convertir
el flujo completo en un patrón compartido de asistente: progreso, título,
descripción, área de contenido, error y acción principal.

### 3.3 Listas y consultas

- Inventario
- Compras
- Ventas
- Clientes
- Proveedores
- Caja
- Cuentas por cobrar
- Cuentas por pagar
- Unidades de medida
- Listas internas del detalle de producto

La mayoría usa `GridStyler`; varias usan `EstadoListaControl` y
`PaginacionControl`. Sin embargo, filtros, toolbars, encabezados, exportación,
acciones por fila y anchos de columnas todavía no responden a un contrato único.

### 3.4 Formularios y diálogos

- Abrir y cerrar caja
- Registrar pago
- Crear categoría rápida
- Crear o editar tercero
- Perfil de tercero
- Registrar compra
- Armar paquete
- Cobro en efectivo
- Configuración del negocio, CAI, usuarios y unidades
- Importación de inventario y compras

Los diálogos pequeños ya se benefician de `FormularioLayout`. Los formularios
medianos y grandes todavía combinan layouts fluidos con alturas, anchos y
etiquetas definidos localmente.

### 3.5 Pantallas complejas

| Pantalla | Tamaño aproximado | Riesgo principal |
|---|---:|---|
| `ProductDetailControl` | 830 líneas | Mezcla formulario, secciones, ayuda, múltiples grillas y flujos secundarios. |
| `PosControl` | 507 líneas | Captura de alta frecuencia; cualquier regresión afecta velocidad de venta. |
| `InventarioControl` | 376 líneas | Combina lista, tarjetas, selección y navegación maestro-detalle. |
| `AjustesControl` | 305 líneas | Agrupa dominios distintos en una sola superficie vertical. |
| `FormRegistrarCompra` | 282 líneas | Transacción con proveedor, líneas, total, crédito y validación. |

Estas pantallas deben migrarse después de estabilizar los componentes que
consumen. No deben usarse como lugar para inventar nuevos patrones.

## 4. Fortalezas que deben conservarse

1. **Paleta definida por roles.** `UiTheme` ya concentra los colores principales,
   neutros y semánticos.
2. **Jerarquía tipográfica inicial.** Existen fuentes base, título, sección,
   secundaria, negrita y total de transacción.
3. **Escala de espaciado.** `UiTheme.Espacio` evita parte de los números mágicos.
4. **Alturas comunes.** `UiTheme.Medidas` define control, fila, encabezado,
   toolbar y barra de estado.
5. **Tablas coherentes.** `GridStyler.Aplicar` establece un buen punto de partida.
6. **Estados de lista.** `EstadoListaControl` diferencia carga, vacío inicial,
   vacío por filtro y error.
7. **Paginación reutilizable.** La navegación de resultados ya tiene un control
   propio.
8. **Botones compartidos.** Ya existen variantes primaria, secundaria, toolbar
   e ícono.
9. **Layout de formulario reutilizable.** Las filas etiqueta-control ya no
   dependen siempre de coordenadas absolutas.
10. **DPI.** `FormBase` utiliza `AutoScaleMode.Dpi` y aplica ícono, fuente y fondo.

El plan debe extender estas piezas; no reemplazarlas con otra biblioteca ni
crear una segunda implementación paralela.

## 5. Inconsistencias detectadas

### 5.1 Tokens incompletos y valores locales

Todavía aparecen fuentes construidas en pantallas concretas, por ejemplo en el
shell, el lanzador de módulos, cobro, compras y POS. También quedan usos directos
de `Color.White`. Aunque varios son visualmente correctos, violan el contrato de
centralización y permiten divergencia futura.

Faltan métricas semánticas para:

- anchos de campos corto, medio, largo y monetario;
- altura de botón e ícono táctil/clickeable;
- ancho máximo de texto explicativo;
- encabezados de página y sección;
- diálogos pequeño, mediano y grande;
- grosor de borde y foco;
- sidebar expandido, colapsado e ítems;
- breakpoints por ancho disponible.

### 5.2 Anatomía de pantalla no obligatoria

Las listas tienden a tener toolbar, filtros, grilla, estado y paginación, pero
cada clase decide cómo apilarlos. Falta un contenedor compartido que asegure:

1. encabezado de página;
2. acción principal y acciones secundarias;
3. filtros con acción de limpiar;
4. contenido o estado alternativo;
5. paginación y resumen.

Sin ese contenedor, dos listas correctas por separado pueden verse diferentes.

### 5.3 Tamaños de campos y formularios

Hay anchos locales como 70, 100, 140, 160, 180, 200, 220, 240, 280, 300,
320, 420 y 480 px. Algunos responden al dato, pero no existe una taxonomía que
explique cuándo usar cada uno.

El problema no es que un campo tenga ancho fijo: un año no debe ocupar todo el
formulario. El problema es que el ancho no expresa un rol reutilizable. Se
necesitan categorías semánticas y reglas de crecimiento.

### 5.4 Jerarquía y orden de botones

`Botones` define estilos, pero no reglas estructurales. Se observan pantallas con
más de una acción primaria, botones `+` o `?` tratados como botones de texto y
acciones de distinta importancia dentro del mismo grupo.

Debe existir una sola acción primaria visible por región. En formularios, el
orden lógico será `Guardar/Confirmar` seguido de `Cancelar`; las acciones
destructivas se separan y nunca ocupan el lugar de la principal. En toolbars, la
creación va primero y las utilidades como importar/exportar se agrupan después.

### 5.5 Ayudas contextuales

Los botones `?` actuales usan tooltips con textos incrustados directamente en
`ProductDetailControl`. Esto presenta cuatro problemas:

- rompe la centralización de textos;
- el símbolo no comunica de manera uniforme si es ayuda, advertencia o detalle;
- el área clickeable y el foco no están definidos;
- un tooltip no es suficiente para explicaciones largas o accesibilidad por
  teclado.

Se necesita un único `BotonAyudaContextual` con tooltip corto, descripción
accesible y capacidad opcional de abrir una explicación más extensa.

### 5.6 Sidebar e inicio

El orden actual es aproximadamente: Menú, Inventario, Proveedores, Clientes,
Compras, POS, Caja, Ventas y Ajustes. Es una lista técnica por entidad/módulo.
No refleja la frecuencia ni el flujo principal de una tienda de repuestos.

Además:

- "Menú" repite el contenido del sidebar;
- POS aparece después de catálogos menos frecuentes;
- Caja y Ventas están separadas del flujo de venta;
- Clientes y Proveedores ocupan dos entradas principales aunque comparten el
  concepto de tercero;
- Ajustes está correctamente al final, pero no está separado visualmente;
- al colapsar, no hay tooltip que identifique el ícono;
- no hay una zona utilitaria explícita para usuario, ayuda y configuración.

### 5.7 Tablas y listas

`GridStyler` resuelve apariencia base, pero faltan contratos para:

- definición de columnas y orden estable;
- anchos mínimos y columnas que pueden crecer;
- alineación por tipo de dato;
- formato de fechas, cantidades, moneda y estados;
- acción principal de la fila;
- doble clic y tecla Enter;
- menú contextual o acciones de fila;
- persistencia o reinicio de selección después de recargar;
- indicador de ordenamiento;
- resumen "mostrando X–Y de Z";
- accesibilidad del estado seleccionado;
- comportamiento con cero filas, error y búsqueda sin resultados.

### 5.8 Estados y feedback

Las listas más nuevas ya distinguen cuatro estados, pero formularios y
transacciones aún dependen de etiquetas de error locales o `MessageBox`.
Falta una jerarquía común:

- error de campo junto al campo;
- resumen de errores cuando varios campos fallan;
- banner no bloqueante para error de carga;
- confirmación breve de guardado;
- diálogo modal solo para decisiones o errores que impiden continuar;
- estado ocupado que deshabilita la acción repetible sin congelar la UI.

### 5.9 Teclado y foco

La guía exige teclado primero, pero el contrato no está codificado. Cada
pantalla debe declarar y probar:

- foco inicial;
- orden de tabulación;
- `Enter` para acción principal cuando no altera un multilinea;
- `Esc` para cancelar o volver;
- `F2` nuevo/editar cuando corresponda;
- `F5` actualizar;
- `Ctrl+F` buscar;
- `Delete` o una alternativa explícita solo para acciones reversibles o
  confirmadas;
- retorno de foco después de guardar, buscar o cerrar un diálogo.

### 5.10 DPI, resolución y texto

El uso de `AutoScaleMode.Dpi` ayuda, pero controles con alturas rígidas, labels
de una sola línea y formularios con `ClientSize` fija pueden cortar contenido a
125 % o 150 %. La revisión estática encontró `AutoScaleMode.Dpi`, pero no una
declaración explícita de `PerMonitorV2` en manifiesto o configuración. El plan
debe verificar el comportamiento real antes de afirmar que el escalado por
monitor está resuelto. Las pantallas deben probarse como mínimo en:

- 1366×768 a 100 %;
- 1366×768 a 125 %;
- 1920×1080 a 100 %;
- 1920×1080 a 150 %.

No se aceptará texto cortado, controles superpuestos, botones fuera de pantalla
ni scroll horizontal de la página completa. Una grilla puede desplazarse
horizontalmente únicamente cuando sus datos realmente lo requieren.

### 5.11 Contradicción documental ya resuelta

La guía general menciona un sidebar de 240 px expandido y 48 px colapsado. El
ADR-0010, el código actual y comentarios posteriores de la propia guía fijan
220 px y 56 px. De acuerdo con la jerarquía documental de `CLAUDE.md`, manda el
ADR. Esta especificación usa 220/56 y el plan deberá corregir la cifra antigua
de la guía para que futuros agentes no vuelvan a abrir la decisión.

## 6. Riesgos de implementación

1. **Migrar pantallas antes que componentes.** Multiplica soluciones locales.
2. **Cambiar POS y compras simultáneamente.** Son dos flujos transaccionales de
   alto riesgo y deben validarse por separado.
3. **Confundir consistencia con uniformidad absoluta.** Un POS necesita mayor
   densidad y un total destacado; un diálogo de categoría no.
4. **Cambiar navegación y permisos juntos.** La presentación puede cambiar sin
   inventar nuevas reglas de autorización.
5. **Usar el diseñador visual como fuente de verdad.** La mayoría de pantallas
   se construye en código; el contrato debe vivir en componentes y pruebas
   manuales, no en coordenadas del diseñador.
6. **Crear un framework interno demasiado grande.** Solo se extraerán patrones
   usados por al menos dos superficies o necesarios para imponer una regla
   transversal.

## 7. Criterios de éxito del programa

El rediseño se considerará completo cuando:

- no haya colores o fuentes visuales fuera de `UiTheme`, salvo impresión con
  excepción documentada;
- todas las listas de primer nivel compartan anatomía, estados y paginación;
- todos los formularios usen tamaños semánticos y orden de acciones común;
- el sidebar esté ordenado por flujo operativo y sea entendible colapsado;
- todos los íconos tengan nombre accesible y tooltip cuando oculten texto;
- no haya textos de ayuda visibles incrustados en controles;
- cada pantalla tenga foco inicial y recorrido completo por teclado;
- la matriz de DPI y resolución pase sin recortes;
- la compilación no agregue errores ni advertencias;
- un nuevo módulo vertical pueda adoptar el sistema sin copiar código de
  `Sistemas.Repuestos.Library`.

## 8. Fuera de alcance

- Reescribir la aplicación en WPF, web u otro framework.
- Cambiar reglas de negocio, stored procedures o modelo de datos por motivos
  visuales.
- Crear un sistema completo de permisos por módulo.
- Implementar modo oscuro antes de cerrar la consistencia del modo claro.
- Incorporar una librería de iconos externa.
- Automatizar la UI con una dependencia nueva.
- Rediseñar impresión de recibos, salvo que se documente una excepción visual
  necesaria para la impresora térmica.
