# Especificación del sistema de diseño

**Estado:** propuesta para aprobación  
**Ámbito:** `Sistemas.Core.UI` y todas las verticales  
**Fuente normativa general:** `GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`

## 1. Objetivo

Definir un contrato visual y de interacción suficientemente preciso para que
dos agentes distintos construyan pantallas que parezcan parte del mismo
producto. Esta especificación describe el resultado; el plan posterior indicará
el orden exacto para implementarlo.

## 2. Principios obligatorios

1. **Una decisión, un propietario.** Colores, fuentes y métricas viven en
   `UiTheme`; construcción visual repetida vive en componentes de Core.
2. **Una pantalla, una tarea principal.** Solo una acción primaria domina el
   flujo activo. Una acción local puede asumir ese rol únicamente cuando la
   acción general no está visible o pertenece a otro modo de la pantalla.
3. **Densidad con ritmo.** Se usa espacio para separar conceptos, no cada
   control individual.
4. **Reconocer antes que recordar.** Etiquetas, títulos y estados explican el
   contexto; el usuario no memoriza códigos ni iconos ambiguos.
5. **El teclado es un camino completo.** El mouse mejora, pero no desbloquea
   acciones inaccesibles por teclado.
6. **Los estados forman parte de la pantalla.** Cargando, vacío, error,
   deshabilitado y éxito no se agregan al final.
7. **Responsive dentro de WinForms.** Dock, Anchor, AutoSize, TableLayoutPanel y
   FlowLayoutPanel mandan sobre coordenadas absolutas.
8. **La vertical compone, Core estandariza.** Ningún componente compartido
   conoce repuestos, vehículos, proveedores o ventas.

## 3. Tokens visuales

### 3.1 Color

Se conserva la paleta Grafito y Vino. Los nombres deben expresar función, no
apariencia. Los roles actuales son la base:

| Rol | Valor actual | Uso permitido |
|---|---|---|
| `Primario` | `#8B2635` | Acción principal, foco activo y acento limitado. |
| `PrimarioOscuro` | `#6E1E2A` | Hover/presión de la acción principal. |
| `SidebarFondo` | `#27272A` | Fondo del shell lateral. |
| `SidebarFondoActivo` | `#38383D` | Hover y selección del sidebar. |
| `SidebarTexto` | `#E7E5E4` | Texto principal del sidebar. |
| `SidebarTextoTenue` | `#A3A09C` | Metadatos del sidebar. |
| `FondoContenido` | `#FAFAF9` | Fondo general de página. |
| `FondoPanel` | `#FFFFFF` | Superficie elevada o agrupada. |
| `TextoOscuro` | `#27272A` | Texto principal. |
| `TextoTenue` | `#6B6864` | Texto secundario y etiquetas. |
| `Borde` | `#E4E1DC` | Divisores sutiles; no reemplaza el indicador de foco. |
| `SeleccionFila` | `#F1E5E7` | Selección de tabla o fondo primario sutil. |
| `Exito` | `#2F7D4F` | Confirmación y estados positivos. |
| `Advertencia` | `#9A6A00` | Riesgo que permite continuar. |
| `Error` | `#C0362C` | Error o acción destructiva. |
| `Info` | `#3E5C76` | Información neutral. |

El plan debe completar roles para fondo de control, control deshabilitado,
texto deshabilitado, hover neutro, divisor fuerte y foco. Los valores finales
se validarán por contraste antes de codificarlos. No se reutilizará `Error` para
datos negativos que no representen un error, ni `Primario` como color de éxito.

Reglas:

- no se usa color como única señal;
- texto normal debe alcanzar contraste 4.5:1;
- bordes funcionales e iconos deben alcanzar 3:1;
- una superficie no usa sombras para simular jerarquía;
- máximo una acción primaria visible para el flujo activo;
- la paleta de gráficos no se usa para estados.

### 3.2 Tipografía

La familia única de interfaz es Segoe UI. La escala compartida es:

| Token | Tamaño | Uso |
|---|---:|---|
| `FuenteTitulo` | 15 pt Semibold | Título de página o diálogo. |
| `FuenteSeccion` | 10 pt Semibold | Encabezado de grupo. |
| `FuenteBase` | 9.5 pt | Controles, tablas y texto principal. |
| `FuenteBaseNegrita` | 9.5 pt Bold | Énfasis corto, totales secundarios y selección. |
| `FuenteSecundaria` | 8 pt | Metadatos y ayudas breves. |
| `FuenteTotal` | 20 pt Semibold | Total principal de una transacción; única excepción. |
| `FuenteGlyph` | 14 pt MDL2 | Iconos comunes. |

Un glifo de lanzador puede tener un token de tamaño propio en `UiTheme`; no
debe construirse localmente con `new Font`. La impresión térmica mantiene
Consolas como excepción documentada porque no pertenece a la interfaz.

No se permiten:

- más escalas por conveniencia local;
- negrita en párrafos completos;
- mayúsculas sostenidas en botones o títulos;
- texto secundario como sustituto de una etiqueta necesaria.

### 3.3 Espaciado

Se conserva `UiTheme.Espacio`:

| Token | px | Aplicación típica |
|---|---:|---|
| `Xxs` | 2 | Ajuste óptico excepcional. |
| `Xs` | 4 | Separación interna muy compacta. |
| `Sm` | 8 | Ícono-texto, controles relacionados. |
| `Md` | 12 | Fila compacta, grupo pequeño. |
| `Lg` | 16 | Separación estándar entre campos o grupos. |
| `Xl` | 24 | Separación de secciones. |
| `Xxl` | 32 | Margen principal de pantalla. |
| `Huge` | 48 | Estado vacío o separación estructural. |

La distancia comunica relación:

- 4–8 px: elementos inseparables;
- 12–16 px: controles del mismo grupo;
- 24–32 px: secciones distintas;
- 48 px: pausa estructural o estado vacío.

No se usarán márgenes arbitrarios fuera de la escala salvo que el comentario
explique un ajuste óptico necesario.

### 3.4 Métricas semánticas

Las medidas deben exponerse mediante tokens, no números locales:

| Rol | Medida objetivo a 100 % DPI |
|---|---:|
| Control estándar | 30 px alto |
| Botón estándar | 30 px mínimo alto |
| Objetivo de solo ícono | 32×32 px mínimo |
| Fila de tabla normal | 28 px |
| Encabezado de tabla | 32 px |
| Toolbar | 48 px mínimo |
| Barra de estado/paginación | 32 px mínimo |
| Ítem de sidebar | 44 px alto |
| Sidebar expandido | 220 px ancho |
| Sidebar colapsado | 56 px ancho |
| Formulario legible | 760 px máximo antes de dividir secciones |

Los valores escalan con DPI. Ninguna pantalla compensa el escalado reduciendo
la fuente.

## 4. Campos de formulario

### 4.1 Anchos semánticos

Los campos se clasifican por el dato esperado:

| Categoría | Ancho base | Ejemplos |
|---|---:|---|
| `MuyCorto` | 72 px | año, cantidad pequeña, porcentaje. |
| `Corto` | 120 px | código corto, días, stock. |
| `Medio` | 220 px | teléfono, RTN, número de factura. |
| `Largo` | 320 px | nombre, correo, selección de producto. |
| `Expandible` | mínimo 320 px, crece | dirección, búsqueda principal. |
| `Multilinea` | mínimo 320×96 px, crece | descripción y observaciones. |

Un campo no ocupa todo el ancho solo porque hay espacio. Su tamaño anticipa la
longitud de la respuesta y facilita escanear el formulario.

### 4.2 Etiquetas

- Se usa una columna de etiqueta estable dentro de cada sección.
- La etiqueta termina sin dos puntos, salvo que el patrón global decida lo
  contrario para todas las pantallas.
- La obligatoriedad se comunica junto a la etiqueta y también mediante
  validación; nunca solo por color.
- "Opcional" se muestra únicamente cuando reduce incertidumbre.
- El texto de ayuda no reemplaza el nombre del campo.
- Una etiqueta nunca queda visualmente debajo o desalineada respecto al campo.

### 4.3 Validación

El orden de presentación es:

1. borde/indicador del campo;
2. mensaje específico debajo del campo cuando puede corregirse allí;
3. resumen superior cuando hay varios errores;
4. foco en el primer campo inválido.

Un error debe decir qué ocurrió y cómo corregirlo. No se borra el contenido del
usuario después de una validación fallida.

### 4.4 Secciones

Un formulario largo se divide por conceptos del negocio, no por conveniencia
del layout. Cada sección contiene:

- título corto;
- descripción solo si evita un error real;
- campos relacionados;
- acciones locales únicamente cuando no compiten con Guardar.

No se usan GroupBox clásicos con borde pesado. La separación se logra con
título, espacio y, cuando haga falta, superficie o divisor.

## 5. Botones y acciones

### 5.1 Variantes

El sistema tendrá variantes explícitas:

- **Primario:** confirma la tarea principal.
- **Secundario:** acción importante pero no dominante.
- **Neutro/terciario:** utilidad de baja jerarquía.
- **Destructivo:** acción irreversible o de alto impacto, con color de error.
- **Icono:** acción compacta con tooltip y nombre accesible obligatorios.
- **Ayuda:** explica sin modificar datos.

### 5.2 Orden

- Formularios: acción primaria, luego cancelar; destructivas separadas.
- Toolbars: crear/nuevo, acciones sobre selección, actualizar, importar/exportar.
- Diálogos: confirmar y cancelar en posición constante en todo el sistema.
- Una acción deshabilitada explica por qué mediante estado o tooltip; no
  desaparece si su ausencia impide entender el flujo.

### 5.3 Texto e iconos

- Los botones usan verbo y objeto cuando pueda existir ambigüedad: "Registrar
  pago", no "Aceptar".
- Un ícono acompaña texto solo cuando mejora reconocimiento.
- Un botón de solo ícono se reserva para acciones conocidas o espacio limitado.
- `+` aislado se reemplaza por glifo estándar y tooltip; si crear es importante,
  se muestra "Nueva categoría" o equivalente.

## 6. Ayuda contextual

Se creará un patrón único para las ayudas `?`:

- glifo de información o ayuda de Segoe MDL2;
- objetivo mínimo de 32×32 px;
- estilo visual neutro, no equivalente a una acción primaria;
- foco por teclado y activación con Enter/Espacio;
- tooltip de una oración, almacenado en `Textos.cs`;
- `AccessibleName` con el formato "Ayuda: <campo>";
- `AccessibleDescription` con la explicación completa;
- explicación ampliada solo cuando el contenido exceda un tooltip breve.

La ayuda explica conceptos desconocidos o consecuencias. No se coloca junto a
campos autoexplicativos ni compensa una etiqueta deficiente.

Ejemplos válidos:

- qué significa stock mínimo y cuándo genera una alerta;
- cómo afecta la unidad de medida a cantidades fraccionarias;
- diferencia entre categoría y etiqueta.

## 7. Tablas y listas

### 7.1 Anatomía obligatoria

Toda lista principal contiene, en este orden:

1. título y descripción opcional;
2. toolbar con acción primaria;
3. filtros y búsqueda;
4. resumen de filtros activos cuando no sea evidente;
5. grilla o estado alternativo;
6. paginación y conteo.

### 7.2 Columnas

- Identificador técnico oculto salvo necesidad operativa.
- Texto a la izquierda.
- números, cantidades y dinero a la derecha.
- fecha corta centrada o a la izquierda de forma consistente.
- estados mediante texto y, opcionalmente, indicador semántico.
- acción principal al final solo si doble clic/Enter no es suficiente.
- una columna flexible absorbe espacio; las demás tienen mínimos por dato.
- encabezados cortos y sin abreviaturas desconocidas.

### 7.3 Interacción

- clic selecciona una fila;
- doble clic y Enter ejecutan la misma acción principal;
- `Ctrl+F` mueve foco a búsqueda;
- `F5` recarga conservando filtros;
- al recargar se conserva selección si la entidad aún existe;
- no se ejecuta una acción sobre una selección obsoleta;
- acciones que requieren fila están visibles y deshabilitadas sin selección.

### 7.4 Estados

Se mantienen los cuatro estados de `EstadoListaControl`:

- cargando;
- vacío inicial, con acción para crear;
- vacío por filtros, con acción para limpiar;
- error, con acción para reintentar.

El estado normal incluye filas y paginación. Nunca se superpone una etiqueta de
error sobre una grilla con datos anteriores sin aclarar que los datos están
desactualizados.

### 7.5 Paginación

La zona de paginación muestra:

- anterior y siguiente;
- página actual y total de páginas;
- rango visible y total de registros cuando el servicio lo proporciona;
- tamaño de página solo si el usuario obtiene un beneficio real.

Los botones extremos quedan deshabilitados, no ocultos.

## 8. Arquetipos de pantalla

### 8.1 Lista/consulta

Usa la anatomía de la sección 7. La acción primaria suele ser "Nuevo". Es el
arquetipo de compras, ventas, terceros, caja y cuentas.

### 8.2 Detalle/edición

Encabezado con volver, título y estado; cuerpo con secciones; barra de acciones
estable. En modo lectura no se presentan campos deshabilitados como si fueran
editables: se muestran valores. En modo edición aparecen controles y acciones
Guardar/Cancelar.

### 8.3 Transacción/captura

Optimizada para velocidad y teclado. Mantiene visibles líneas, total y acción de
confirmación. POS y registrar compra comparten estructura conceptual, pero no
necesitan idéntica densidad.

### 8.4 Inicio/tablero

No es una cuadrícula decorativa de módulos. Debe responder: qué requiere
atención, qué acciones son frecuentes y cómo entrar al trabajo. Mientras no
existan métricas confiables, usa accesos recientes/frecuentes y estados
operativos reales; no inventa gráficos vacíos.

### 8.5 Configuración/catálogo simple

Secciones claramente tituladas, explicación de impacto, formularios cortos y
acciones locales. Ajustes no debe parecer una lista continua de controles sin
jerarquía.

## 9. Feedback y mensajes

| Situación | Presentación |
|---|---|
| Error corregible de campo | Mensaje junto al campo y foco. |
| Error de carga recuperable | Banner/estado con Reintentar. |
| Operación exitosa sin cambio de pantalla | Confirmación breve no bloqueante. |
| Decisión irreversible | Diálogo de confirmación con verbo específico. |
| Información que bloquea el flujo | Diálogo informativo. |
| Operación en curso | Acción deshabilitada, indicador y UI responsiva. |

Los mensajes técnicos se registran; el usuario recibe una explicación en
español y una acción posible.

## 10. Accesibilidad y teclado

Cada pantalla documenta:

- `TabIndex` completo y sin saltos ilógicos;
- foco inicial;
- acción de Enter;
- comportamiento de Escape;
- atajos disponibles;
- nombre accesible de iconos;
- relación entre etiqueta y control;
- contraste y señal alternativa al color.

Los tooltips no contienen información indispensable que no pueda descubrirse
por teclado. El foco debe ser visible sobre fondo claro y oscuro.

## 11. Responsive, DPI y scroll

- El layout principal se construye con contenedores fluidos.
- Un formulario centrado no supera su ancho máximo legible.
- Al reducir ancho, dos columnas pasan a una antes de comprimir campos por
  debajo de su tamaño semántico.
- El scroll pertenece al área de contenido, no al shell completo.
- Encabezados y acciones principales permanecen visibles cuando el flujo lo
  requiere.
- Labels explicativos usan AutoSize y ancho máximo, no altura fija arbitraria.
- Todas las superficies se verifican en la matriz de resolución definida en el
  diagnóstico.

## 12. Contrato de componentes compartidos

La implementación deberá ofrecer, como mínimo, piezas con estas
responsabilidades, aunque el plan podrá ajustar nombres para seguir el código:

| Componente | Responsabilidad única |
|---|---|
| Tema/tokens | Colores, fuentes, espaciado, medidas y anchos semánticos. |
| Fábrica de botones | Variantes, estados, iconos y accesibilidad. |
| Ayuda contextual | Tooltip, foco, nombre y explicación ampliada. |
| Encabezado de página | Título, descripción, volver y acciones. |
| Toolbar de lista | Acción primaria, acciones de selección y utilidades. |
| Barra de filtros | Búsqueda, filtros, aplicar y limpiar. |
| Contenedor de lista | Grilla, estado, paginación y transición entre estados. |
| Layout de formulario | Etiquetas, campos, errores y cambio de columnas. |
| Encabezado de sección | Título, descripción y acción local opcional. |
| Banner de estado | Info, éxito, advertencia o error recuperable. |

No se crea una superclase que conozca todos los casos. Se prefieren controles
pequeños y composición.

## 13. Reglas para verticales futuras

Una vertical puede proporcionar:

- nombre, glifo, orden y vista de un módulo;
- campos y secciones propios del dominio;
- columnas y acciones de su entidad;
- textos de negocio en su `Textos.cs`.

No puede proporcionar:

- otra paleta o familia tipográfica;
- su propia versión de toolbar, paginación o estado vacío;
- colores o fuentes sueltos;
- una navegación paralela dentro del shell;
- componentes compartidos que nombren su dominio en Core.

## 14. Definición de conformidad de una pantalla

Una pantalla cumple esta especificación cuando:

1. corresponde a un arquetipo declarado;
2. usa tokens y componentes compartidos;
3. tiene una sola acción primaria por región;
4. cubre estados normal, ocupado, vacío/error cuando apliquen;
5. se opera completamente con teclado;
6. pasa la matriz de DPI y resolución;
7. no contiene texto, fuente o color visual suelto;
8. presenta errores accionables;
9. mantiene arquitectura y reglas de negocio existentes;
10. tiene evidencia de revisión en la matriz de migración.
