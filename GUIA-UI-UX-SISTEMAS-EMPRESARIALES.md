# Guía de Diseño Visual y de Interacción para Sistemas Empresariales de Escritorio

**Stack objetivo:** .NET 10 (WinForms / WPF) + SQL Server Express 2025
**Alcance:** cómo se diseña el *sistema* — espacio, jerarquía, navegación, ciclo de vida de pantallas — no sus funcionalidades.
**Usuario objetivo del software:** empleado no técnico, sin entrenamiento previo, que va a usar la aplicación 6–9 horas diarias, todos los días, durante años.

> Esta guía es agnóstica de framework. Los principios aplican igual en WinForms y WPF; donde la implementación difiere, hay notas y código de referencia para ambos.

---

## Índice

1. [Los seis principios que gobiernan todo lo demás](#1-los-seis-principios-que-gobiernan-todo-lo-demás)
2. [La ley de la pantalla: anatomía fija del shell](#2-la-ley-de-la-pantalla-anatomía-fija-del-shell)
3. [Sistema de espacio: la rejilla de 4/8 px](#3-sistema-de-espacio-la-rejilla-de-48-px)
4. [Densidad: cuánta información por pantalla](#4-densidad-cuánta-información-por-pantalla)
5. [Jerarquía tipográfica](#5-jerarquía-tipográfica)
6. [Uso correcto de la paleta: colores como roles, no como decoración](#6-uso-correcto-de-la-paleta-colores-como-roles-no-como-decoración)
7. [Las cinco pantallas canónicas de todo sistema empresarial](#7-las-cinco-pantallas-canónicas-de-todo-sistema-empresarial)
8. [Patrones de formulario](#8-patrones-de-formulario)
9. [Patrones de tabla / grilla](#9-patrones-de-tabla--grilla)
10. [Navegación y ciclo de vida de pantallas](#10-navegación-y-ciclo-de-vida-de-pantallas) ← *el corazón de la arquitectura visual*
11. [Reconstruir el contenido dentro de una pantalla](#11-reconstruir-el-contenido-dentro-de-una-pantalla)
12. [Estados, feedback y errores](#12-estados-feedback-y-errores)
13. [Teclado: la diferencia entre un sistema usable y uno odiado](#13-teclado-la-diferencia-entre-un-sistema-usable-y-uno-odiado)
14. [Realidad de campo: DPI, resoluciones, hardware viejo](#14-realidad-de-campo-dpi-resoluciones-hardware-viejo)
15. [Código de referencia](#15-código-de-referencia)
16. [Checklist de QA visual](#16-checklist-de-qa-visual)
17. [Anti-patrones que matan sistemas empresariales](#17-anti-patrones-que-matan-sistemas-empresariales)
18. [Fuentes](#18-fuentes)

---

## 1. Los seis principios que gobiernan todo lo demás

Un sistema empresarial no se diseña como una app de consumo. El usuario no viene a "descubrir" ni a "disfrutar": viene a ejecutar la misma tarea 200 veces al día. La métrica de éxito no es que le guste, es **segundos por transacción y errores por turno**.

### 1.1 Consistencia por encima de creatividad

Si el botón primario está abajo a la derecha en una pantalla, está abajo a la derecha en las 40 pantallas. Si Escape cierra sin guardar en una, lo hace en todas. Cada excepción cuesta un re-aprendizaje que el usuario paga con errores.

**Regla operativa:** antes de diseñar una pantalla nueva, pregúntate a cuál de las cinco pantallas canónicas (sección 7) se parece, y cópiale la estructura. Una pantalla original es una falla de análisis, no un logro.

### 1.2 Reconocer, no recordar

El usuario no debe memorizar códigos, secuencias ni ubicaciones. Todo lo que necesita para decidir debe estar visible o a un hover de distancia:

- El combo de producto muestra `[COD-1023] Filtro de aceite Toyota 1.6 — L. 185.00 — 12 en stock`, no `COD-1023`.
- Los campos que el sistema puede deducir vienen prellenados y editables.
- Las acciones se llaman por lo que hacen (`Guardar y facturar`), no por su nombre técnico (`Procesar`).

### 1.3 Densidad con ritmo, no amontonamiento

"Que no se vea amontonado" **no** significa poner todo con mucho aire. Un sistema con demasiado aire obliga a hacer scroll y a saltar entre pantallas, y eso es más caro que la densidad. Lo que evita el amontonamiento no es el espacio total, es el **espacio diferencial**: los elementos relacionados se pegan, los grupos distintos se separan.

> Un formulario con 30 campos correctamente agrupados en 5 bloques se lee mejor que uno con 12 campos sueltos flotando con márgenes gigantes.

### 1.4 El sistema siempre dice qué está pasando

Nada ocurre en silencio. Toda operación que pase de ~300 ms muestra progreso; toda operación que cambie datos confirma con un mensaje concreto (`Factura 000-001-01-00001234 emitida`), no con un `OK`.

### 1.5 El error se previene primero, se explica después

Deshabilitar lo que no aplica, validar mientras se escribe, confirmar solo lo destructivo. Y cuando falle: qué pasó, por qué, y qué hacer — en el idioma del usuario, nunca `Error 547: FK constraint violated`.

### 1.6 Teclado primero, mouse opcional

Un cajero o bodeguero factura con el teclado. Si tu flujo de captura obliga a soltar el teclado para hacer clic, el sistema es lento por diseño. Toda la captura de datos debe ser posible sin tocar el mouse.

---

## 2. La ley de la pantalla: anatomía fija del shell

La aplicación entera es **una sola ventana** con regiones fijas. El usuario aprende dónde está cada cosa una vez y ese aprendizaje se transfiere a todo el sistema.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ A · Barra de identidad     Sistema Repuestos · Sucursal Centro · Ana Márquez │ 40px
├───────────────┬──────────────────────────────────────────────────────────────┤
│               │ C · Encabezado de contenido                                  │
│  B · Nav      │    Productos                                    [+ Nuevo]    │ 56px
│  lateral      ├──────────────────────────────────────────────────────────────┤
│               │ D · Barra de filtros/búsqueda                                │ 48px
│  Inicio       ├──────────────────────────────────────────────────────────────┤
│  Ventas       │                                                              │
│  Inventario   │ E · Cuerpo (la única región que cambia)                      │
│  ▸ Productos  │                                                              │
│    Categorías │                                                              │
│    Ajustes    │                                                              │
│  Compras      │                                                              │
│  Clientes     │                                                              │
│  Reportes     ├──────────────────────────────────────────────────────────────┤
│               │ F · Barra de acciones      [Cancelar]  [Guardar]             │ 56px
├───────────────┴──────────────────────────────────────────────────────────────┤
│ G · Barra de estado   Conectado · BD local · 1,204 productos · v1.4.2        │ 24px
└──────────────────────────────────────────────────────────────────────────────┘
    240px
```

**Reglas de cada región:**

| Región | Contenido | Nunca |
|---|---|---|
| **A** Identidad | Nombre del sistema, sucursal/empresa activa, usuario, menú de sesión | Acciones de la pantalla actual |
| **B** Navegación | Módulos y sub-módulos. Máximo 2 niveles. El ítem activo se marca | Más de 7±2 ítems de primer nivel; iconos sin texto |
| **C** Encabezado | Título de la pantalla (= nombre del ítem de nav), migas si hay detalle, acción primaria de creación | Título distinto al del menú |
| **D** Filtros | Búsqueda, filtros, selector de rango. Solo en pantallas de lista | Filtros escondidos tras un icono sin etiqueta |
| **E** Cuerpo | Lo único que se reemplaza al navegar | Que cambie el ancho de B o el alto de A/G |
| **F** Acciones | Acciones de commit del contenido actual, alineadas a la derecha, primaria al extremo | Acciones que floten dentro del cuerpo y desaparezcan al hacer scroll |
| **G** Estado | Conexión a BD, contadores, versión, mensajes transitorios | Información crítica que el usuario deba leer para operar |

**Por qué esta estructura y no un menú superior clásico:** el menú lateral vertical escala a 20+ pantallas sin submenús en cascada, mantiene visible el "dónde estoy" todo el día, y en pantallas anchas (16:9, que es todo lo que se vende) el espacio horizontal sobra y el vertical falta. Un menú desplegable de Windows 98 obliga a recordar en qué menú vivía cada opción.

**Ancho de la navegación:** 240 px expandida, 48 px colapsada (solo iconos + tooltip). El colapso lo decide el usuario y se persiste; no lo colapses automáticamente por ancho de ventana, eso desorienta.

---

## 3. Sistema de espacio: la rejilla de 4/8 px

Todo el espaciado del sistema sale de una escala fija. Nada de "le puse 7 píxeles porque se veía bien". Esto es lo que hace que un sistema se vea *ordenado* aunque lo diseñe alguien que no es diseñador: la regularidad se percibe como profesionalismo.

### 3.1 La escala

Base **4 px**, con los múltiplos de 8 como valores dominantes (es la práctica de Fluent 2, Material y Carbon):

| Token | Valor | Uso |
|---|---|---|
| `Space.Xxs` | 2 px | Ajustes ópticos de iconos |
| `Space.Xs` | 4 px | Etiqueta ↔ su control, icono ↔ su texto |
| `Space.Sm` | 8 px | Entre controles del mismo grupo, padding interno de botones |
| `Space.Md` | 12 px | Padding interno de tarjetas/paneles pequeños |
| `Space.Lg` | 16 px | **Separación entre campos de un formulario**, padding de contenedores |
| `Space.Xl` | 24 px | **Separación entre grupos de campos**, margen del cuerpo de pantalla |
| `Space.Xxl` | 32 px | Separación entre secciones mayores |
| `Space.Huge` | 48 px | Espacio en blanco intencional (estados vacíos, pantallas de bienvenida) |

**Prohibido** cualquier valor fuera de la escala. Si necesitas 14 px, usa 12 o 16.

### 3.2 La regla que evita el amontonamiento

> **El espacio dentro de un grupo debe ser visiblemente menor que el espacio entre grupos.** Proporción mínima 1:2.

```
Datos generales                     ← título de grupo
  Código        [__________]        ← 4px entre etiqueta y control
  Descripción   [__________]        ← 16px entre campos  (Space.Lg)
  Categoría     [__________]
                                    ← 24px entre grupos  (Space.Xl)
Precios
  Costo         [__________]
  Precio venta  [__________]
  ISV           [__________]
```

Si todo está separado por lo mismo (12 px, digamos), el ojo no puede agrupar y el formulario se percibe como una lista plana de 30 cosas: **eso es lo que se siente "amontonado", no la falta de espacio**. Es la ley de proximidad de Gestalt, y es más barata que cualquier línea divisoria: prefiere el espacio antes que un separador gris.

### 3.3 Márgenes de pantalla

- Margen exterior del cuerpo: **24 px** arriba/abajo/izquierda/derecha.
- Padding interno de un panel o tarjeta: **16 px**.
- Un panel dentro de otro panel: baja un nivel de la escala; no anides más de 2 niveles de contenedor con borde. Tres marcos anidados es el look clásico de "sistema hecho por programador".

### 3.4 Ancho de los controles: el error #1 de los sistemas caseros

**El ancho de un campo debe comunicar la longitud esperada del dato.** Un campo de fecha estirado a 600 px es una mentira visual y hace que el formulario se vea desordenado aunque el espaciado sea perfecto.

| Dato | Ancho sugerido (100% DPI) |
|---|---|
| Cantidad, ISV, porcentaje | 80–100 px |
| Fecha | 120 px |
| Código / SKU | 140 px |
| Precio, monto | 140 px |
| Teléfono, RTN | 180 px |
| Nombre, razón social | 280–360 px |
| Descripción, dirección | 100% del contenedor (o multilínea) |

Y **limita el ancho total del área de formulario a ~720–840 px** aunque la ventana esté maximizada en un monitor de 27". Un formulario de 1900 px de ancho obliga a mover los ojos de un extremo a otro y destruye la relación etiqueta–campo. El espacio sobrante a la derecha se usa para un panel secundario (resumen, historial, ayuda) o simplemente se deja vacío. **Espacio vacío intencional ≠ espacio desperdiciado.**

---

## 4. Densidad: cuánta información por pantalla

El usuario profesional prefiere ver más y hacer menos scroll. La densidad correcta para un sistema empresarial de escritorio es **más alta que la de una web moderna** — pero se logra reduciendo alturas y paddings, nunca reduciendo el espacio entre grupos.

### 4.1 Alturas de referencia a 100% DPI

| Elemento | Compacto | **Normal (default)** | Cómodo |
|---|---|---|---|
| Alto de control (textbox, combo, botón) | 26 px | **30 px** | 34 px |
| Alto de fila de grilla | 24 px | **28 px** | 34 px |
| Alto de encabezado de grilla | 28 px | **32 px** | 36 px |
| Alto de fila de menú lateral | 32 px | **36 px** | 40 px |
| Alto de barra de herramientas | 40 px | **48 px** | 56 px |

> Nota: las guías web (p. ej. Pencil & Paper) recomiendan filas de 40/48/56 px. Eso es para tablas con avatares y contenido rico en navegador. Para una grilla de escritorio con texto y números, 24–32 px es lo correcto y es lo que usan SAP, Dynamics, Odoo en modo lista y todo POS serio. **No copies alturas de guías web sin traducir el contexto.**

### 4.2 Densidad conmutable

Si el sistema se va a usar tanto en laptops de 1366×768 como en monitores grandes, ofrece un selector de densidad (Compacto / Normal / Cómodo) en preferencias y **persístelo por usuario**. Es una de las funciones de mayor retorno por línea de código: en 1366×768 la diferencia entre 28 px y 34 px de fila son 4 filas visibles más, y eso son minutos por turno.

### 4.3 El presupuesto de la pantalla

Regla práctica para una pantalla de lista en 1366×768:

- Cromo fijo (barra identidad + encabezado + filtros + acciones + estado) ≤ **220 px**
- Quedan ~548 px de cuerpo → **18–19 filas visibles a 28 px**

Si tu cromo se come 350 px, quedan 12 filas y el usuario hará 50% más scroll toda su vida laboral. **Cada píxel de cromo permanente se paga todos los días.** Audita esto explícitamente.

---

## 5. Jerarquía tipográfica

Una sola familia. En Windows: **Segoe UI** (o `Segoe UI Variable` en Win11). Nada de mezclar fuentes; la jerarquía se hace con tamaño, peso y color, no con familias distintas.

| Rol | Tamaño | Peso | Color | Uso |
|---|---|---|---|---|
| Título de pantalla | **15 px** (11 pt) | SemiBold | Texto primario | Región C |
| Título de sección | 13 px (10 pt) | SemiBold | Texto primario | Encabezado de grupo de campos |
| Cuerpo / controles | **12 px (9 pt)** | Regular | Texto primario | Todo lo demás |
| Etiqueta de campo | 12 px (9 pt) | Regular | Texto secundario | Labels |
| Secundario / ayuda | 11 px (8 pt) | Regular | Texto terciario | Hints, timestamps, unidades |
| Números en grilla | 12 px | Regular, **tabular** | Texto primario | Montos, cantidades |

**Máximo 4 tamaños en todo el sistema.** Más que eso y la jerarquía deja de leerse como jerarquía.

**Números tabulares:** activa cifras de ancho fijo en columnas numéricas para que los decimales se alineen ópticamente. En WPF: `TextOptions.TextFormattingMode` + una fuente con `tnum`, o usa `Consolas`/`Cascadia Mono` solo para columnas de montos si tu fuente base no tiene tabulares. En WinForms es más simple usar formato `N2` con alineación a la derecha (sección 9).

**Mayúsculas:** solo para etiquetas de sección muy cortas, con letter-spacing. Nunca en botones ni en datos: `L. 1,250.00` es legible, `L. 1,250.00` en mayúsculas no aporta nada y `GUARDAR` grita.

---

## 6. Uso correcto de la paleta: colores como roles, no como decoración

Aquí está la clave de tu pregunta: no importa *qué* colores elegiste, importa **a qué rol semántico está asignado cada uno y con qué frecuencia aparece**.

### 6.1 Convierte tu paleta en tokens de rol

Nunca escribas un color en el código de una pantalla. Define una vez, en un solo archivo, una tabla de roles. Todo el sistema consume roles.

| Token | Rol | Cuántas veces aparece en pantalla |
|---|---|---|
| `Surface` | Fondo de la aplicación / cuerpo | Toda el área |
| `SurfaceRaised` | Fondo de paneles, tarjetas, encabezado de grilla | Zonas agrupadas |
| `SurfaceSunken` | Fondo de áreas de entrada, filas alternas | Sutil |
| `Border` | Separadores y bordes de control (bajo contraste) | Muchas, casi invisibles |
| `BorderStrong` | Borde de control enfocado, bordes de tabla | Pocas |
| `TextPrimary` | Datos, títulos | Mayoría del texto |
| `TextSecondary` | Etiquetas, encabezados de columna | Etiquetas |
| `TextDisabled` | Deshabilitado | Excepcional |
| `Accent` | **Acción primaria y solo eso** | **1 por pantalla** |
| `AccentHover` / `AccentPressed` | Estados del acento | — |
| `AccentSubtle` | Fondo del ítem activo de navegación, fila seleccionada | 1–2 zonas |
| `Success` / `SuccessBg` | Estado positivo confirmado | Solo en badges/mensajes |
| `Warning` / `WarningBg` | Advertencia, requiere atención | Solo en badges/mensajes |
| `Danger` / `DangerBg` | Error, acción destructiva | Solo en badges/mensajes |
| `Info` / `InfoBg` | Informativo, neutro | Solo en badges/mensajes |

### 6.2 Las cuatro reglas de uso del color

**Regla 1 — 60/30/10.** 60% superficies neutras, 30% texto y bordes, **10% color**. Si tu pantalla tiene el menú de color, los encabezados de color, los botones de color y los badges de color, ya no hay jerarquía: cuando todo destaca, nada destaca.

**Regla 2 — Una acción primaria por pantalla.** El color de acento es el que dice "esto es lo que vienes a hacer aquí". Si hay dos botones de acento, el usuario duda. Todo lo demás son botones secundarios (borde + texto) o terciarios (solo texto).

```
[Cancelar]  [Guardar borrador]  [ Emitir factura ]
 terciario    secundario          acento ← uno solo
```

**Regla 3 — El color nunca es el único portador de información.** Un ~8% de los hombres tiene alguna deficiencia de color, y muchos de tus usuarios trabajarán con monitores TN baratos y mal calibrados. Todo estado lleva **color + texto (+ icono)**:

```
MAL:   ●            ●            ●          (solo el color distingue el estado)
BIEN:  ● Vencida    ● Pendiente   ● Pagada
```

**Regla 4 — Contraste mínimo 4.5:1** para texto normal contra su fondo, 3:1 para bordes de controles y texto grande. Verifícalo con una herramienta, no a ojo: los grises claros sobre blanco que se ven "elegantes" en tu monitor son ilegibles en el monitor de la tienda a las 3 pm con sol entrando.

### 6.3 Dónde SÍ va el color (y dónde no)

| Sí | No |
|---|---|
| Botón de acción primaria | Fondo de la barra de navegación entera en color saturado |
| Indicador de ítem activo en el menú (barra de 3 px + fondo sutil) | Encabezados de grilla en color de marca |
| Badges de estado de documento | Bordes de todos los paneles |
| Fila seleccionada (fondo `AccentSubtle`) | Alternancia de filas en color (usa un gris a 2–3% de diferencia, o nada) |
| Validación en línea (borde `Danger` + mensaje) | Texto de datos en colores |
| Totales que requieren atención (saldo vencido) | Iconos multicolor decorativos |

### 6.4 Modo oscuro

En .NET 10 el modo oscuro de WinForms ya no es experimental: `Application.SetColorMode(SystemColorMode.System)` y los controles siguen el modo del sistema. Si vas a soportarlo:

- Define la tabla de roles **dos veces** (claro/oscuro) y consume siempre por token. Si ya escribiste colores literales en las pantallas, agregar modo oscuro después es rehacer el sistema.
- En oscuro, **no uses negro puro** (`#000`) ni blanco puro para texto: `#1A1A1A`–`#202020` de fondo y `#E8E8E8` de texto reducen el halo.
- En oscuro, la elevación se expresa con superficies *más claras*, no con sombras.
- Los colores de acento y de estado suelen necesitar más luminosidad en oscuro para mantener 4.5:1.

Si el proyecto es v1 y el tiempo es corto: **solo modo claro, pero tokenizado**. Es una decisión legítima; lo que no es legítimo es hardcodear colores.
---

## 7. Las cinco pantallas canónicas de todo sistema empresarial

El 90% de un ERP, un sistema de ferretería, uno de repuestos o uno de RH cabe en cinco arquetipos. Define cada uno **una sola vez** como plantilla y deriva todas las pantallas de ahí. Esto es lo que hace que 40 pantallas se sientan como un solo producto.

### 7.1 Lista / Consulta (el arquetipo dominante)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Productos                                            [+ Nuevo producto]│
├──────────────────────────────────────────────────────────────────────┤
│ [Buscar código o descripción...        ]  Categoría ▾  Estado ▾  [Limpiar] │
├──────────────────────────────────────────────────────────────────────┤
│ Código  │ Descripción            │ Categoría │ Existencia│  Precio │  │
│ ────────┼────────────────────────┼───────────┼───────────┼─────────┼──│
│ FIL-001 │ Filtro aceite Toyota   │ Filtros   │        12 │  185.00 │⋮ │
│ FIL-002 │ Filtro aire Nissan     │ Filtros   │         3 │  240.00 │⋮ │
│ BAT-010 │ Batería 12V 65Ah       │ Baterías  │         0 │ 2,450.00│⋮ │
│                                                                       │
├──────────────────────────────────────────────────────────────────────┤
│ 1,204 productos · 18 con existencia baja      ‹ 1 2 3 … 25 ›          │
└──────────────────────────────────────────────────────────────────────┘
```

Reglas:
- La búsqueda tiene el **foco al abrir la pantalla**. Siempre.
- Filtros visibles, no escondidos. Máximo 4 en la barra; el resto en un panel "Más filtros".
- Los filtros activos se muestran como chips removibles y se persisten al volver a la pantalla.
- Doble clic en la fila = acción por defecto (abrir detalle). También `Enter` sobre la fila seleccionada.
- La columna de acciones por fila va **al final**, con un menú `⋮`, no con 5 botones por fila.
- El pie de tabla lleva el conteo total y la paginación. Un conteo es información operativa real ("¿cuántas facturas van hoy?").

### 7.2 Detalle / Edición

```
┌──────────────────────────────────────────────────────────────────────┐
│ ‹ Productos  /  FIL-001                                               │
│ Filtro de aceite Toyota 1.6                          ● Activo         │
├─────────────────────────────────────────┬────────────────────────────┤
│                                          │                            │
│  Datos generales                         │  Resumen                   │
│    Código        [FIL-001    ]           │   Existencia      12 und   │
│    Descripción   [_______________]       │   Costo prom.  L. 120.00   │
│    Categoría     [Filtros    ▾]          │   Margen           35.1%   │
│                                          │   Últ. compra  02/09/2026  │
│  Precios                                 │                            │
│    Costo         [   120.00]             │  Actividad reciente        │
│    Precio venta  [   185.00]             │   • Venta  -2  hoy 10:14   │
│    ISV           [ 15%     ▾]            │   • Compra +20 02/09       │
│                                          │                            │
│  Inventario                              │                            │
│    Mínimo        [     5]                │                            │
│    Ubicación     [Pasillo 3 ]            │                            │
├─────────────────────────────────────────┴────────────────────────────┤
│                                        [Cancelar]  [Guardar cambios]  │
└──────────────────────────────────────────────────────────────────────┘
```

Reglas:
- Migas de pan que devuelven a la lista **conservando su estado** (filtros, página, scroll, fila seleccionada). Esto es no negociable: perder los filtros al volver es la queja #1 de usuarios de sistemas internos.
- Formulario a la izquierda con ancho acotado; panel de contexto de solo lectura a la derecha (ahí se va el espacio sobrante de los monitores anchos).
- Estado del registro visible en el encabezado como badge.
- Barra de acciones fija abajo, nunca flotando dentro del área con scroll.
- Si hay cambios sin guardar, cualquier salida (navegar, cerrar, cambiar de módulo) pide confirmación. Esto lo maneja el `INavigationService` (sección 10), no cada pantalla por su cuenta.

### 7.3 Transacción / Captura (factura, entrada de inventario, orden)

La pantalla más crítica del sistema: es donde el usuario pasa la mayor parte del día y donde cada segundo se multiplica por cientos.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Nueva factura                                    Fecha 09/09/2026     │
├──────────────────────────────────────────────────────────────────────┤
│ Cliente [Consumidor final          ▾][+]   RTN [____________]        │
├──────────────────────────────────────────────────────────────────────┤
│ Producto [_________________________][ Agregar ]        ← foco aquí   │
├──────────────────────────────────────────────────────────────────────┤
│ Cant │ Código  │ Descripción           │ P. Unit │  Desc │    Total  │
│    2 │ FIL-001 │ Filtro aceite Toyota  │  185.00 │  0.00 │    370.00 │
│    1 │ BAT-010 │ Batería 12V 65Ah      │2,450.00 │ 50.00 │  2,400.00 │
│                                                                       │
│                                          (área que crece)             │
├──────────────────────────────────────────────────────────────────┬───┤
│                                              Subtotal   L. 2,770.00  │
│                                              ISV 15%    L.   415.50  │
│                                              TOTAL      L. 3,185.50  │  ← 20px, SemiBold
├──────────────────────────────────────────────────────────────────────┤
│ [Cancelar (Esc)]                       [Guardar (F10)] [Cobrar (F12)] │
└──────────────────────────────────────────────────────────────────────┘
```

Reglas específicas:
- **Un solo campo de captura recibe el foco al abrir y lo recupera después de cada línea agregada.** El operador escribe código → Enter → cantidad → Enter → vuelve al campo de producto. Cero clics.
- El total va en el tamaño tipográfico más grande de todo el sistema. Es el dato por el que el usuario y el cliente están parados ahí.
- Nada de diálogos modales en medio del flujo de captura. Si falta el cliente, se crea desde un panel lateral o un modal *corto* que devuelve el foco exactamente donde estaba.
- Atajos de función visibles en los botones (`Cobrar (F12)`), porque así se aprenden sin manual.
- El error de una línea (sin existencia, precio en cero) se marca **en la línea**, no en un MessageBox que tapa la pantalla.

### 7.4 Inicio / Tablero

No es un dashboard de BI. Para un empleado sin entrenamiento, el inicio es un **panel de arranque de tareas**, no de gráficos.

- 4–6 indicadores máximo, cada uno **clicable hacia la lista filtrada que lo produce** (el "18 productos con existencia baja" abre productos filtrados por existencia baja).
- Accesos directos a las 3–4 acciones que ese rol hace todos los días.
- Nada de gráficos si nadie toma decisiones con ellos. Un gráfico decorativo consume espacio permanente y ancho de banda cognitivo.

### 7.5 Configuración / Catálogo simple

Listas maestras cortas (categorías, unidades, sucursales, impuestos). Aquí sí se justifica edición **en línea** o modal pequeño; no montes un flujo de detalle completo para un catálogo de 12 filas.

---

## 8. Patrones de formulario

### 8.1 Una columna por defecto

Una sola columna se escanea más rápido y evita ambigüedad en el orden de tabulación. **Usa dos columnas solo** cuando los campos son cortos y forman pares naturales (Costo/Precio, Desde/Hasta, Departamento/Municipio). Nunca 3 columnas.

### 8.2 Etiquetas

Dos opciones válidas, **elige una y úsala en todo el sistema**:

| | Etiqueta arriba | Etiqueta a la izquierda |
|---|---|---|
| Velocidad de lectura | Mayor | Menor |
| Espacio vertical | Consume más | Consume menos |
| Alineación de campos | Perfecta | Requiere columna de etiquetas de ancho fijo |
| Recomendado para | Formularios de captura largos | Formularios densos de consulta/edición |

Si eliges izquierda: alinea las etiquetas **a la derecha**, pegadas a su campo (8 px), con una columna de ancho fijo. Etiquetas alineadas a la izquierda con campos alineados a la izquierda crean un "río" de espacio irregular que se ve desordenado.

Nunca uses el placeholder como etiqueta: desaparece al escribir, y el usuario que se distrae ya no sabe qué campo es.

### 8.3 Agrupación

- Grupos de **3 a 7 campos**. Más de 7 → subdivide.
- Título de grupo en SemiBold, sin marco. **El marco (`GroupBox`) es opcional y casi siempre innecesario**: el espacio ya agrupa. Si usas marcos, que sean líneas de 1 px en `Border`, no marcos 3D.
- Más de 4 grupos en una pantalla → considera pestañas *dentro* del detalle (General / Precios / Inventario / Contabilidad). Pestañas dentro del contenido, nunca ventanas separadas.

### 8.4 Campos obligatorios, opcionales y validación

- Marca lo obligatorio con `*` **y** menciona en el encabezado del grupo que lo demás es opcional. Si el 90% es obligatorio, marca lo *opcional* en vez de lo obligatorio.
- **Validación al salir del campo** (`Validating` / `LostFocus`), no en cada tecla — validar mientras se escribe muestra "correo inválido" cuando el usuario apenas va por la tercera letra, y eso irrita.
- Los errores se muestran **debajo del campo, en texto**, en `Danger`, con borde del control en `Danger`. Un `ErrorProvider` de WinForms con solo el icono rojo obliga a hacer hover para saber qué pasó: acompáñalo siempre de texto.
- Al intentar guardar con errores: mueve el foco al primer campo inválido y haz scroll hasta él. No muestres un MessageBox listando errores.

### 8.5 Valores por defecto y trabajo repetitivo

El usuario que registra 80 entradas de inventario iguales agradece más los valores por defecto inteligentes que cualquier detalle visual: fecha = hoy, sucursal = la del usuario, ISV = el configurado, proveedor = el último usado en la sesión. Cada default correcto es un campo menos que tocar 80 veces.

### 8.6 Solo lectura vs deshabilitado

- **Deshabilitado** (gris, sin borde de foco): el control podría habilitarse si cambia algo. Explica por qué con un tooltip.
- **Solo lectura** (sin caja de entrada, texto plano): el dato es informativo y nunca editable aquí. No pongas un `TextBox` gris con `ReadOnly`; imprime el valor como texto. Reduce ruido visual enormemente.

---

## 9. Patrones de tabla / grilla

La grilla es el componente donde más se gana y más se pierde en un sistema empresarial.

### 9.1 Alineación (regla mecánica, sin excepciones)

| Tipo de dato | Alineación | Encabezado |
|---|---|---|
| Texto, descripciones, nombres | Izquierda | Izquierda |
| Números de cantidad y montos | **Derecha** | **Derecha** |
| Fechas, códigos, RTN, teléfonos | Izquierda | Izquierda |
| Badges de estado, iconos | Centro | Centro |

Los montos van a la derecha con formato `N2` y separador de miles (`L. 1,250.00`), para que los decimales se alineen verticalmente y el ojo compare magnitudes de un vistazo. El encabezado debe alinearse igual que su contenido; encabezado a la izquierda sobre números a la derecha es ruido visual puro.

### 9.2 Columnas

- **Máximo 7–9 columnas visibles.** Lo demás va al detalle o a un panel expandible de fila.
- Orden: identificador → descripción → dimensiones (categoría, fecha) → medidas (cantidad, monto) → estado → acciones.
- La columna descriptiva es la que absorbe el ancho sobrante (`Fill`); las demás llevan ancho fijo o `AutoSize` por contenido. Que la columna "Existencia" mida 300 px porque `AutoSizeColumnsMode = Fill` reparte parejo es un error clásico y hace ver la tabla vacía y desordenada.
- **Encabezado congelado** al hacer scroll vertical; primera columna congelada si hay scroll horizontal.
- Permite reordenar/ocultar columnas y **persiste esa preferencia por usuario y por pantalla**. Es barato y el usuario lo percibe como un sistema "que se adapta a él".

### 9.3 Filas

- Sin bordes verticales entre celdas. Solo una línea horizontal de 1 px en `Border`, o zebra muy sutil — **una de las dos, nunca ambas**. La rejilla completa tipo Excel (`CellBorderStyle = Single` en todas las direcciones) es lo que hace que una pantalla se vea de 1998 y se sienta amontonada.
- Fila seleccionada con fondo `AccentSubtle` y **una barra de 3 px en el borde izquierdo**; no inviertas todo el texto a blanco sobre azul saturado.
- Hover sutil (`SurfaceSunken`) para dar sensación de respuesta.
- Sin ajuste de línea (`WrapMode = False`): filas de altura uniforme, texto largo truncado con elipsis + tooltip. Las filas de altura variable destruyen el ritmo vertical y la capacidad de escanear.

### 9.4 Semántica de fila y celda

Resalta con color solo lo que exige acción: existencia en cero, factura vencida, saldo negativo. Y siempre con color de fondo **sutil** (`DangerBg` al 10–15%) más un badge de texto, nunca fila roja intensa. Si el 40% de las filas están coloreadas, el color dejó de significar algo.

### 9.5 Selección múltiple y acciones masivas

- Checkbox en la primera columna, y **la barra de acciones masivas aparece solo cuando hay selección**, reemplazando la barra de filtros o superponiéndose al pie: `3 seleccionados · [Exportar] [Cambiar categoría] [Desactivar]`.
- `Ctrl+A`, `Shift+clic` y `Ctrl+clic` deben funcionar como en Windows. No inventes.

### 9.6 Paginación vs scroll infinito

Para sistemas empresariales: **paginación del lado del servidor** (`OFFSET/FETCH` en tus SPs), 50 filas por página. Razones: el usuario necesita saber cuántos registros hay, poder decir "está en la página 3", y tu grilla no debe cargar 40,000 filas en memoria. El scroll infinito impide referirse a una posición y complica la impresión/exportación.

Alternativa válida en grillas locales pequeñas: **virtualización** (`VirtualMode` en `DataGridView`, virtualización nativa en `ListView`/`DataGrid` de WPF).

### 9.7 Los cuatro estados obligatorios de toda grilla

Toda pantalla que muestre datos debe tener diseñados los cuatro:

1. **Cargando** — overlay ligero o skeleton, con la estructura ya visible. Nunca una pantalla en blanco.
2. **Vacío inicial** (no hay datos aún) — mensaje + explicación + acción: *"Aún no hay productos registrados. [+ Crear el primero]"*.
3. **Vacío por filtro** (sí hay datos, el filtro no devuelve nada) — mensaje **distinto** del anterior: *"Ningún producto coincide con «bateria 90ah». [Limpiar filtros]"*. Confundir estos dos estados hace que el usuario crea que perdió su información.
4. **Error** — qué falló, y un botón `Reintentar`. Nunca una grilla vacía silenciosa cuando la consulta falló.
---

## 10. Navegación y ciclo de vida de pantallas

Esta es la decisión arquitectónica que más determina si el sistema se siente profesional o casero. Tu pregunta exacta — *"¿qué tan común es crear y destruir pantallas, o actualizar una sola pantalla reconstruyendo lo de adentro?"* — tiene una respuesta clara en la industria.

### 10.1 Qué hacen los sistemas reales

| Modelo | Descripción | Estado en la industria |
|---|---|---|
| **A. Una ventana (`Form`) por cada cosa** | `new FrmProductos().Show()` desde el menú, cada pantalla es una ventana flotante | **Muerto.** Es lo que hacían los sistemas VB6/Delphi de los 90. El usuario termina con 9 ventanas apiladas, perdiendo la de atrás, sin saber cuál está activa |
| **B. MDI** (ventanas hijas dentro de una ventana padre) | `IsMdiContainer = true` | **Obsoleto.** Microsoft lo desaconseja desde Vista; no encaja con DPI por monitor, no encaja con Win11, y los usuarios manejan mal ventanas dentro de ventanas |
| **C. Shell + región de contenido** | Una sola ventana; la región del cuerpo se reemplaza al navegar | **El estándar actual.** SAP Fiori, Dynamics 365, Odoo, Sage, Shopify POS, todo sistema web moderno, y todo cliente de escritorio serio |
| **D. Shell + pestañas de documento** | Como C, pero el usuario puede tener varias pantallas abiertas como pestañas | **C con esteroides.** Necesario cuando el trabajo exige comparar o alternar (contabilidad, cotizaciones) |

**Recomendación para tu producto: modelo C**, con la puerta abierta a D si el rubro lo exige (facturación + consulta de inventario simultáneas, por ejemplo).

Las ventanas separadas quedan reservadas para tres casos puntuales, y ninguno más:

1. **Diálogos modales cortos** — confirmar, seleccionar un registro, capturar 2–5 campos, un wizard de 3 pasos. Duración objetivo: menos de 30 segundos.
2. **Ventanas de utilidad genuinamente paralelas** — una calculadora, un visor de documento, un monitor de báscula. Modal = no; siempre encima = sí.
3. **Segundo monitor** — si el usuario debe ver dos pantallas del sistema a la vez y no quieres implementar pestañas, permitir "abrir en ventana nueva" una vista concreta. Es la excepción, no el patrón.

### 10.2 La arquitectura: shell, región y servicio de navegación

```
        MainShell (única ventana)
        ├── Regiones fijas (identidad, nav, estado)
        └── ContentHost  ← un contenedor vacío
                 ▲
                 │  el NavigationService inserta/quita aquí
                 │
        ┌────────┴─────────┬──────────────────┐
   ProductListView   ProductDetailView   InvoiceView  ...
   (UserControl /    (UserControl /      (UserControl /
    UserControl WPF)  UserControl WPF)    UserControl WPF)
```

**La unidad de pantalla no es un `Form`, es un `UserControl`.** Esa sola decisión resuelve el 80% del problema: un `UserControl` se puede insertar en el shell, en una pestaña, en un panel lateral o — si algún día hace falta — dentro de un `Form` modal, sin reescribir nada.

Contrato mínimo, agnóstico de framework:

```csharp
public interface IScreen
{
    string Title { get; }
    Task OnNavigatedToAsync(NavigationContext ctx);   // cargar datos, restaurar estado
    Task<bool> CanNavigateAwayAsync();                // false = cancelar la salida (cambios sin guardar)
    void OnNavigatedFrom(NavigationContext ctx);      // guardar estado de vista, soltar recursos
}

public interface INavigationService
{
    Task<bool> NavigateToAsync<TScreen>(object? parameter = null) where TScreen : IScreen;
    Task<bool> GoBackAsync();
    event EventHandler<NavigationEventArgs> Navigated;
}
```

Las pantallas **nunca** se instancian entre sí (`new FrmDetalleProducto()` dentro de la lista es el acoplamiento que después impide meterla en una pestaña). Las pantallas piden navegación al servicio:

```csharp
await _navigation.NavigateToAsync<ProductDetailScreen>(new { ProductId = id });
```

### 10.3 ¿Crear y destruir, o reutilizar? La respuesta corta

> **Destruir la vista, conservar el estado.**

La vista (los controles) es cara de mantener viva y barata de reconstruir. El estado de la vista (qué filtros tenía, qué página, qué fila estaba seleccionada) es barato de mantener vivo y **carísimo de perder**, porque el costo lo paga el usuario en tiempo y frustración.

La mayoría de sistemas caseros hace exactamente lo contrario: mantienen la ventana viva en un `static` para "no tener que recargar", y así arrastran datos obsoletos, controles con estado sucio y fugas de memoria; o la destruyen todo y el usuario pierde sus filtros cada vez que consulta un producto.

Separa las dos cosas:

```csharp
// Vive fuera de la vista, en el servicio de navegación. Un objeto pequeño, serializable.
public sealed class ProductListState
{
    public string SearchTerm { get; set; } = "";
    public int? CategoryId { get; set; }
    public int Page { get; set; } = 1;
    public string SortColumn { get; set; } = "Codigo";
    public int SelectedId { get; set; }
    public double ScrollOffset { get; set; }
}
```

Al salir, `OnNavigatedFrom` escribe ese objeto en el servicio. Al volver, `OnNavigatedToAsync` lo lee, repuebla los filtros, ejecuta la consulta y restaura la selección. La vista se creó de cero (limpia, sin estado sucio, sin fugas) pero **para el usuario es como si nunca se hubiera ido**.

### 10.4 Matriz de decisión: destruir, cachear o mantener viva

| Situación | Estrategia |
|---|---|
| Pantalla normal de lista o detalle | **Crear al entrar, destruir al salir**, con `ViewState` persistido |
| Pantalla visitada constantemente y cara de construir (grilla con 15 columnas configurables, muchos combos) | **Caché LRU de 3–5 vistas**. Se mantiene viva pero se le notifica `OnNavigatedFrom`/`OnNavigatedToAsync` para que refresque datos |
| Pantalla de captura con trabajo a medias (factura en curso, entrada de inventario en curso) | **Mantener viva mientras el documento esté abierto** — idealmente como pestaña visible, para que el usuario sepa que sigue ahí. Jamás en un `static` invisible |
| Diálogo modal | Crear, mostrar, **`Dispose` siempre** (`using`) |
| Shell y regiones fijas | Vivas toda la sesión |

**Sobre el caché:** empieza sin caché. Mide. Si construir la pantalla toma menos de ~150 ms, el usuario no lo percibe y el caché solo te agrega bugs de estado obsoleto. Optimiza cuando tengas la medición, no antes.

**Regla de oro del caché:** una vista cacheada **siempre** recarga sus datos en `OnNavigatedToAsync`. Mostrar la grilla con los datos de hace 20 minutos porque "estaba en caché" es peor que tardar 200 ms en recargar: en un sistema multiusuario, otro empleado ya movió el inventario.

### 10.5 Ciclo de vida completo

```
NavigateToAsync<T>()
    │
    ├─► pantalla actual: CanNavigateAwayAsync()
    │       └─ false → cancelar navegación (hay cambios sin guardar)
    │
    ├─► pantalla actual: OnNavigatedFrom()
    │       ├─ guardar ViewState en el servicio
    │       ├─ cancelar operaciones en vuelo (CancellationToken)
    │       └─ desuscribir eventos externos
    │
    ├─► quitar la vista del ContentHost
    │       └─ si no va a caché: Dispose()
    │
    ├─► obtener la vista destino (del caché o del contenedor DI)
    │
    ├─► insertar en ContentHost
    │
    └─► destino: OnNavigatedToAsync(ctx)
            ├─ restaurar ViewState
            ├─ mostrar estado "cargando"
            ├─ consultar datos (await, sin bloquear la UI)
            └─ enfocar el control de entrada primario
```

### 10.6 Fugas de memoria: las cuatro causas reales

Si vas a crear y destruir vistas todo el día durante 9 horas, esto importa de verdad. Un sistema de escritorio que crece 4 MB por navegación es inutilizable al final del turno.

1. **Eventos no desuscritos.** Si tu vista se suscribe a un evento de un objeto de vida larga (un servicio, un timer, `SystemEvents`, un singleton de sesión), el objeto de vida larga mantiene viva la vista para siempre. Desuscribe en `OnNavigatedFrom`/`Dispose`. Es, de lejos, la causa #1.
2. **`Dispose` no llamado.** En WinForms, cada control es un handle Win32. Quitar el control del `Controls` collection **no lo libera**: hay que llamar `Dispose()`. Los `Form` modales necesitan `using`. Los `Image`, `Font`, `Brush`, `SqlConnection` también.
3. **Timers vivos.** Un `System.Windows.Forms.Timer` o `DispatcherTimer` de una vista destruida sigue disparando y sigue manteniendo la referencia. Párralo y libéralo.
4. **Estáticos con estado.** `public static FrmProductos Instancia` es la forma más rápida de acumular basura y estado sucio. Si necesitas una sola instancia, que la gestione el contenedor DI con vida `Scoped`, no un `static`.

**Verificación:** deja el sistema navegando entre 5 pantallas 200 veces (o hazlo a mano 30 veces) y observa el contador `GDI Objects` y `User Objects` del Administrador de tareas, además de la memoria. Si suben monótonamente, hay fuga. El límite por proceso de objetos GDI en Windows es 10,000: un sistema con fuga de handles se cuelga con errores gráficos raros antes de quedarse sin RAM.

### 10.7 Modales: cuándo sí y cómo

Un modal bloquea al usuario. Se justifica solo si la tarea es **corta, atómica y bloqueante por naturaleza**:

- Confirmar una acción destructiva.
- Seleccionar un registro de un catálogo grande (buscador de productos/clientes).
- Capturar los 3 campos mínimos de una entidad nueva sin salir del flujo actual (crear cliente en medio de una factura).

Reglas:
- Ancho máximo ~600 px, alto según contenido. **Un modal a pantalla completa es una pantalla mal diseñada como modal.**
- `Esc` cancela, `Enter` confirma la acción primaria, foco inicial en el primer campo editable.
- Al cerrar, **devuelve el foco exactamente al control desde donde se abrió**. Esto es lo que hace que un flujo de captura no se sienta roto.
- Nunca abras un modal desde otro modal. Si te pasa, el flujo está mal descompuesto.
- El resultado se devuelve como dato (`DialogResult` + propiedad, o `Task<TResult>`), nunca escribiendo directamente sobre los controles del llamador.

### 10.8 Cuando el usuario necesita dos cosas a la vez

Antes de dar ventanas flotantes, considera en este orden:

1. **Panel lateral (drawer)** dentro de la misma pantalla — para ver el detalle de la fila seleccionada sin salir de la lista. Es lo que hace Outlook y lo que hace Odoo. Barato y muy efectivo.
2. **Fila expandible** — para 3–6 datos adicionales.
3. **Pestañas de documento** (modelo D) — cuando de verdad son tareas paralelas de larga duración.
4. **Ventana nueva** — solo para el caso del segundo monitor.

---

## 11. Reconstruir el contenido dentro de una pantalla

La otra mitad de tu pregunta: *cómo actualizar lo que hay dentro de una pantalla sin crear otra*.

### 11.1 Reconstruir datos ≠ reconstruir controles

| Cambia... | Qué hacer |
|---|---|
| Los **datos** (nuevo filtro, otra página, otro registro) | **Rebind.** Los controles ya existen; solo cambia el origen de datos. `grid.DataSource = resultado;` |
| El **modo** de la pantalla (nuevo / edición / solo lectura) | Cambiar propiedades (`Enabled`, `ReadOnly`, visibilidad de botones) desde **un solo método** `ApplyMode(ScreenMode mode)` |
| La **estructura** (formulario dinámico según tipo de producto, campos configurables) | Reconstruir controles, pero contra un contenedor dedicado y con `SuspendLayout` |
| La **pantalla completa** | Navegación (sección 10) |

El error costoso es tratar el caso 1 como caso 3: limpiar el panel y volver a crear 40 controles cada vez que el usuario cambia de registro. Es lento, parpadea, pierde el foco y filtra handles.

### 11.2 Un solo lugar que decide el estado visual

En vez de esparcir `btnGuardar.Enabled = false` por 12 manejadores de eventos, centraliza:

```csharp
private void ApplyState()
{
    bool editing   = _mode is ScreenMode.New or ScreenMode.Edit;
    bool hasChanges= _model.IsDirty;
    bool canDelete = _mode == ScreenMode.Edit && _permissions.Can("Producto.Eliminar");

    pnlForm.Enabled     = editing;
    btnGuardar.Enabled  = editing && hasChanges;
    btnEliminar.Visible = canDelete;
    btnNuevo.Visible    = _mode == ScreenMode.View;
    lblEstado.Text      = _mode switch
    {
        ScreenMode.New  => "Nuevo producto",
        ScreenMode.Edit => "Editando",
        _               => ""
    };
}
```

Llama `ApplyState()` después de cada cambio relevante. Una sola función que se puede leer completa es la diferencia entre una pantalla mantenible y una donde nadie entiende por qué el botón está gris.

### 11.3 Evitar el parpadeo (esto es lo que hace ver "barato" a un sistema)

```csharp
// WinForms
grid.SuspendLayout();
try
{
    grid.DataSource = null;
    grid.DataSource = data;
}
finally { grid.ResumeLayout(); }

// Además, en el Form o UserControl contenedor:
protected override CreateParams CreateParams
{
    get
    {
        var cp = base.CreateParams;
        cp.ExStyle |= 0x02000000;   // WS_EX_COMPOSITED — elimina el parpadeo al redibujar
        return cp;
    }
}
```

- `ListView.BeginUpdate()/EndUpdate()`, `ComboBox.BeginUpdate()/EndUpdate()` para cargas masivas.
- `DoubleBuffered = true` en el `DataGridView` (vía reflexión o subclase; la propiedad es protegida).
- En WPF el parpadeo casi no existe si usas binding; aparece cuando reconstruyes el árbol visual a mano. No lo hagas: usa `DataTemplate` + `ItemsSource`.
- **Nunca** llames `Application.DoEvents()`. Es la solución aparente que crea reentrada y bugs imposibles de reproducir. Usa `async/await`.

### 11.4 Nunca bloquees el hilo de UI

Toda llamada a SQL Server va en `async` con `CancellationToken`, y la pantalla muestra su estado de "cargando". Con la lógica de negocio en procedimientos almacenados, esto es especialmente importante: un SP pesado deja la ventana en blanco con "No responde" si lo llamas sincrónicamente, y el usuario cree que el sistema se colgó.

```csharp
private CancellationTokenSource? _cts;

private async Task LoadAsync()
{
    _cts?.Cancel();                       // cancelar la búsqueda anterior
    _cts = new CancellationTokenSource();
    var token = _cts.Token;

    SetBusy(true);
    try
    {
        var rows = await _repo.BuscarProductosAsync(_state.SearchTerm, _state.Page, token);
        if (token.IsCancellationRequested) return;
        grid.DataSource = rows;
        lblTotal.Text = $"{rows.TotalCount:N0} productos";
        ShowEmptyStateIfNeeded(rows);
    }
    catch (OperationCanceledException) { /* navegó o volvió a escribir: ignorar */ }
    catch (SqlException ex)
    {
        ShowErrorState("No se pudo consultar el inventario.", ex);
    }
    finally { SetBusy(false); }
}
```

Nota el patrón de cancelación: es lo que permite una búsqueda que responde mientras el usuario escribe (con *debounce* de ~300 ms) sin que lleguen resultados desordenados.
---

## 12. Estados, feedback y errores

### 12.1 Los tiempos que importan

| Duración | Qué mostrar |
|---|---|
| < 100 ms | Nada. Se percibe instantáneo |
| 100–300 ms | Nada, o cursor de espera |
| 300 ms – 2 s | Indicador de carga **en la región afectada**, no en toda la pantalla |
| 2 – 10 s | Barra de progreso + texto de qué se está haciendo + botón `Cancelar` |
| > 10 s | Progreso determinado con pasos ("Procesando 340 de 1,200 facturas"), cancelable, y la app sigue usable si es posible |

**Bloquea lo mínimo.** Si estás cargando la grilla, deshabilita la grilla — no la aplicación entera. El overlay a pantalla completa con "Espere..." es una salida de emergencia, no un patrón.

### 12.2 Confirmaciones y mensajes

Tres canales, y cada uno tiene su lugar:

| Canal | Cuándo | Ejemplo |
|---|---|---|
| **Inline** (junto al control) | Validación de un campo | *"El código FIL-001 ya existe"* bajo el textbox |
| **Banner en la pantalla** | Resultado de la operación de la pantalla, o advertencia contextual | *"Factura 000-001-01-00001234 emitida correctamente. [Imprimir]"* |
| **Modal** | Solo para confirmar algo destructivo o irreversible | *"¿Anular la factura 00001234? Esta acción no se puede deshacer."* |

Un `MessageBox` por cada guardado exitoso es tortura: son 200 clics extra al día. El éxito se comunica con un banner que se desvanece a los 4 segundos y con el hecho evidente de que la lista ya muestra el registro nuevo.

**Anatomía de un mensaje de error útil:**

```
MAL:   "Error al guardar."
MAL:   "System.Data.SqlClient.SqlException: The INSERT statement conflicted
        with the FOREIGN KEY constraint FK_Producto_Categoria"

BIEN:  "No se pudo guardar el producto.
          La categoría seleccionada ya no existe; es posible que otro usuario
          la haya eliminado.
          [Actualizar categorías]   [Cancelar]

          Detalle técnico ▾   (colapsado, copiable, con el código de error)"
```

Qué pasó → por qué → qué puede hacer el usuario → detalle técnico escondido pero copiable (tu soporte remoto lo va a agradecer). Nunca `Contacte al administrador del sistema` a secas: en una ferretería de Choloma **no hay** administrador del sistema.

En WinForms usa `TaskDialog` (disponible y estable en .NET moderno) en vez de `MessageBox`: permite título, instrucción principal, texto explicativo, botones con etiquetas propias (`Emitir factura` en vez de `Sí`) y área expandible de detalle. Botones etiquetados con verbos concretos reducen errores frente a Sí/No.

### 12.3 Deshacer en vez de confirmar

Cuando sea técnicamente viable, prefiere **acción inmediata + deshacer** sobre **confirmación previa**. Confirmar todo entrena al usuario a hacer clic en `Sí` sin leer, y entonces la confirmación ya no protege nada. Reserva la confirmación modal para lo verdaderamente irreversible (anular un documento fiscal, cerrar caja).

---

## 13. Teclado: la diferencia entre un sistema usable y uno odiado

### 13.1 Convenciones que no debes inventar

| Tecla | Acción |
|---|---|
| `Tab` / `Shift+Tab` | Siguiente / anterior campo, **en orden visual** |
| `Enter` | Confirmar el diálogo o ejecutar la acción por defecto |
| `Esc` | Cancelar / cerrar el modal / limpiar la búsqueda |
| `F1` | Ayuda de la pantalla actual |
| `F2` | Editar el elemento seleccionado |
| `F3` | Buscar / buscar siguiente |
| `F5` | Refrescar |
| `Ctrl+N` / `Ctrl+S` / `Ctrl+P` | Nuevo / Guardar / Imprimir |
| `Ctrl+F` | Enfocar la búsqueda |
| `Supr` | Eliminar el seleccionado (con confirmación) |
| `Alt+letra` | Acceso rápido de menús y botones (usa `&` en los textos) |

Para pantallas de captura intensiva, define además teclas de función propias y **muéstralas en los botones** (`Cobrar (F12)`), o en una barra fija inferior estilo POS. El usuario las aprende solo, en dos días, sin manual.

### 13.2 Orden de tabulación

- Debe seguir el orden visual de lectura: izquierda→derecha, arriba→abajo. Revisa `TabIndex` de cada pantalla explícitamente; el orden que asigna el diseñador es el orden en que arrastraste los controles, no el orden correcto.
- Los controles deshabilitados y decorativos se sacan del recorrido (`TabStop = false`).
- El foco inicial de cada pantalla está definido y es el correcto: la búsqueda en una lista, el primer campo editable en un formulario, el campo de producto en una factura.
- El foco visible siempre: un borde de 2 px en `Accent`. Nunca elimines el indicador de foco por estética.

### 13.3 Prueba obligatoria

Completa un flujo de negocio completo (crear producto, facturar, cobrar) **desconectando el mouse**. Si no puedes, tus usuarios de captura tampoco, y estarán perdiendo horas cada semana.

---

## 14. Realidad de campo: DPI, resoluciones, hardware viejo

Tu mercado son negocios pequeños que compran laptops de gama baja y monitores viejos. Diseña para eso:

- **Resolución mínima de soporte: 1366×768.** Toda pantalla debe ser usable ahí sin scroll horizontal. Si tu diseño necesita 1920×1080, la mitad de tus clientes tendrá una mala experiencia.
- **Ventana mínima: 1024×700.** Define `MinimumSize` en el shell y respétalo al diseñar.
- **DPI:** habilita `PerMonitorV2` en el manifiesto / `app.config` y **prueba a 125% y 150%**, que es lo que traen de fábrica muchas laptops. Los síntomas de no hacerlo: texto cortado, botones que se salen, controles superpuestos.
  - Usa layouts que fluyen (`TableLayoutPanel`/`FlowLayoutPanel` en WinForms, `Grid`/`StackPanel` en WPF) en vez de posiciones absolutas. Un formulario con todo en `Location` absoluto se rompe garantizado a 150%.
  - `AutoScaleMode = Dpi` en cada `Form` y `UserControl`.
  - Iconos en SVG (WPF) o mapas de bits a 16/20/24/32 px (WinForms), no un solo PNG escalado.
- **Sin conexión:** el sistema debe verse y comportarse igual sin internet. Nada de fuentes web, iconos de CDN, ni imágenes remotas.
- **Impresión:** la factura/reporte impresa es parte del diseño del sistema. Papel carta y ticket de 80 mm son formatos distintos, no el mismo diseño escalado.

---

## 15. Código de referencia

Todo lo siguiente es esqueleto listo para adaptar. Está pensado para .NET 10 con inyección de dependencias (`Microsoft.Extensions.DependencyInjection` + `Microsoft.Extensions.Hosting`), que ya es el estándar en WinForms y WPF modernos.

> **Sobre el código:** es esqueleto de referencia, no un paquete compilable tal cual. Tipos auxiliares como `Theme.Current`, `Fonts`, `NavigationEventArgs`, `IProductRepository` o `FormLayout.CreateGroup` quedan como puntos de extensión evidentes; la idea es que copies la *estructura* — contratos, ciclo de vida, separación estado/vista — no que pegues archivos.

### 15.1 Tokens de diseño (compartido)

```csharp
namespace SistemasHN.Core.UI;

/// <summary>Escala de espaciado 4/8. Ningún valor fuera de aquí.</summary>
public static class Space
{
    public const int Xxs = 2;   public const int Xs  = 4;
    public const int Sm  = 8;   public const int Md  = 12;
    public const int Lg  = 16;  public const int Xl  = 24;
    public const int Xxl = 32;  public const int Huge= 48;
}

public static class Sizes
{
    public const int ControlHeight    = 30;
    public const int RowHeight        = 28;
    public const int HeaderRowHeight  = 32;
    public const int NavItemHeight    = 36;
    public const int ToolbarHeight    = 48;
    public const int StatusBarHeight  = 24;
    public const int NavWidth         = 240;
    public const int NavWidthCollapsed= 48;
    public const int FormMaxWidth     = 760;
}

/// <summary>Roles semánticos. Cambiar aquí = cambiar todo el sistema.</summary>
public interface IThemeColors
{
    Color Surface { get; }        Color SurfaceRaised { get; }  Color SurfaceSunken { get; }
    Color Border { get; }         Color BorderStrong { get; }
    Color TextPrimary { get; }    Color TextSecondary { get; }  Color TextDisabled { get; }
    Color Accent { get; }         Color AccentHover { get; }    Color AccentSubtle { get; }
    Color Success { get; }        Color SuccessBg { get; }
    Color Warning { get; }        Color WarningBg { get; }
    Color Danger { get; }         Color DangerBg { get; }
    Color Info { get; }           Color InfoBg { get; }
}

public sealed class LightTheme : IThemeColors
{
    // Sustituye estos valores por tu paleta; conserva los ROLES.
    public Color Surface        => Color.FromArgb(0xFA, 0xFA, 0xFB);
    public Color SurfaceRaised  => Color.White;
    public Color SurfaceSunken  => Color.FromArgb(0xF2, 0xF3, 0xF5);
    public Color Border         => Color.FromArgb(0xE3, 0xE5, 0xE8);
    public Color BorderStrong   => Color.FromArgb(0xC4, 0xC7, 0xCC);
    public Color TextPrimary    => Color.FromArgb(0x1B, 0x1D, 0x21);
    public Color TextSecondary  => Color.FromArgb(0x5C, 0x60, 0x68);
    public Color TextDisabled   => Color.FromArgb(0x9A, 0x9E, 0xA6);
    public Color Accent         => Color.FromArgb(0x1E, 0x5E, 0xD6);
    public Color AccentHover    => Color.FromArgb(0x18, 0x4C, 0xB0);
    public Color AccentSubtle   => Color.FromArgb(0xE8, 0xF0, 0xFE);
    public Color Success        => Color.FromArgb(0x1B, 0x7A, 0x3D);
    public Color SuccessBg      => Color.FromArgb(0xE7, 0xF5, 0xEC);
    public Color Warning        => Color.FromArgb(0x9A, 0x6A, 0x00);
    public Color WarningBg      => Color.FromArgb(0xFD, 0xF3, 0xDC);
    public Color Danger         => Color.FromArgb(0xB3, 0x26, 0x1E);
    public Color DangerBg       => Color.FromArgb(0xFC, 0xEA, 0xE9);
    public Color Info           => Color.FromArgb(0x1E, 0x5E, 0xD6);
    public Color InfoBg         => Color.FromArgb(0xE8, 0xF0, 0xFE);
}
```

En WPF el equivalente es un `ResourceDictionary` con los mismos nombres, consumido siempre con `{DynamicResource Accent}` (dinámico, para poder cambiar de tema en caliente):

```xml
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation">
    <SolidColorBrush x:Key="Surface"       Color="#FAFAFB"/>
    <SolidColorBrush x:Key="SurfaceRaised" Color="#FFFFFF"/>
    <SolidColorBrush x:Key="Border"        Color="#E3E5E8"/>
    <SolidColorBrush x:Key="TextPrimary"   Color="#1B1D21"/>
    <SolidColorBrush x:Key="TextSecondary" Color="#5C6068"/>
    <SolidColorBrush x:Key="Accent"        Color="#1E5ED6"/>
    <!-- ... -->
    <system:Double x:Key="SpaceLg">16</system:Double>
    <Thickness x:Key="FormFieldMargin">0,0,0,16</Thickness>
</ResourceDictionary>
```

### 15.2 Contrato de pantalla y estado de vista

```csharp
namespace SistemasHN.Core.Navigation;

public enum ScreenMode { View, New, Edit }

public sealed class NavigationContext
{
    public object? Parameter { get; init; }
    public bool IsReturningBack { get; init; }
    public IViewStateStore State { get; init; } = default!;
}

public interface IViewStateStore
{
    T GetOrCreate<T>(string key) where T : new();
    void Set<T>(string key, T value);
}

public interface IScreen
{
    string Title { get; }
    Task OnNavigatedToAsync(NavigationContext ctx);
    Task<bool> CanNavigateAwayAsync();
    void OnNavigatedFrom(NavigationContext ctx);
}

/// <summary>Marca una pantalla como cara de construir: el servicio la mantiene en caché LRU.</summary>
public interface ICacheableScreen { }
```

### 15.3 Servicio de navegación (WinForms)

```csharp
using Microsoft.Extensions.DependencyInjection;

namespace SistemasHN.Winforms.Navigation;

public sealed class NavigationService : INavigationService, IDisposable
{
    private readonly Control _host;                 // el panel ContentHost del shell
    private readonly IServiceProvider _services;
    private readonly IViewStateStore _state;
    private readonly Dictionary<Type, UserControl> _cache = new();
    private readonly LinkedList<Type> _lru = new();
    private readonly Stack<(Type Type, object? Param)> _history = new();
    private const int MaxCached = 4;

    private UserControl? _current;

    public event EventHandler<NavigationEventArgs>? Navigated;

    public NavigationService(Control host, IServiceProvider services, IViewStateStore state)
        => (_host, _services, _state) = (host, services, state);

    public async Task<bool> NavigateToAsync<TScreen>(object? parameter = null)
        where TScreen : IScreen
        => await NavigateCoreAsync(typeof(TScreen), parameter, isBack: false);

    private async Task<bool> NavigateCoreAsync(Type screenType, object? parameter, bool isBack)
    {
        // 1. ¿Puede salir la pantalla actual?
        if (_current is IScreen currentScreen && !await currentScreen.CanNavigateAwayAsync())
            return false;

        var ctx = new NavigationContext { Parameter = parameter, IsReturningBack = isBack, State = _state };

        // 2. Desmontar la actual
        if (_current is not null)
        {
            (_current as IScreen)?.OnNavigatedFrom(ctx);
            _host.Controls.Remove(_current);

            if (_current is ICacheableScreen)
                Touch(_current.GetType());
            else
                _current.Dispose();          // libera handles Win32: imprescindible
        }

        // 3. Obtener la destino (caché o nueva instancia del contenedor DI)
        UserControl view;
        if (_cache.TryGetValue(screenType, out var cached))
        {
            view = cached;
        }
        else
        {
            view = (UserControl)_services.GetRequiredService(screenType);
            if (view is ICacheableScreen) AddToCache(screenType, view);
        }

        // 4. Montar
        view.Dock = DockStyle.Fill;
        _host.SuspendLayout();
        _host.Controls.Add(view);
        _host.ResumeLayout();
        _current = view;

        if (!isBack) _history.Push((screenType, parameter));
        Navigated?.Invoke(this, new NavigationEventArgs(screenType, (view as IScreen)?.Title ?? ""));

        // 5. Cargar datos (async, con la vista ya visible mostrando "cargando")
        if (view is IScreen destination)
            await destination.OnNavigatedToAsync(ctx);

        return true;
    }

    public async Task<bool> GoBackAsync()
    {
        if (_history.Count < 2) return false;
        _history.Pop();                                   // la actual
        var (type, param) = _history.Peek();
        return await NavigateCoreAsync(type, param, isBack: true);
    }

    private void AddToCache(Type t, UserControl v)
    {
        _cache[t] = v; _lru.AddFirst(t);
        while (_lru.Count > MaxCached)
        {
            var evict = _lru.Last!.Value; _lru.RemoveLast();
            if (_cache.Remove(evict, out var old)) old.Dispose();
        }
    }

    private void Touch(Type t)
    {
        if (_lru.Remove(t)) _lru.AddFirst(t);
    }

    public void Dispose()
    {
        foreach (var v in _cache.Values) v.Dispose();
        _cache.Clear();
        _current?.Dispose();
    }
}
```

### 15.4 Clase base de pantalla (WinForms)

```csharp
public class ScreenBase : UserControl, IScreen
{
    private CancellationTokenSource? _cts;
    private readonly List<Action> _cleanups = new();

    public virtual string Title => "";

    protected ScreenBase()
    {
        AutoScaleMode = AutoScaleMode.Dpi;
        Padding = new Padding(Space.Xl);         // margen del cuerpo, uniforme en todo el sistema
        BackColor = Theme.Current.Surface;
        DoubleBuffered = true;
    }

    /// <summary>Registra una desuscripción para ejecutarla al salir. Evita la fuga #1.</summary>
    protected void OnCleanup(Action action) => _cleanups.Add(action);

    protected CancellationToken ResetToken()
    {
        _cts?.Cancel(); _cts?.Dispose();
        _cts = new CancellationTokenSource();
        return _cts.Token;
    }

    public virtual Task OnNavigatedToAsync(NavigationContext ctx) => Task.CompletedTask;
    public virtual Task<bool> CanNavigateAwayAsync() => Task.FromResult(true);

    public virtual void OnNavigatedFrom(NavigationContext ctx)
    {
        _cts?.Cancel();
        foreach (var c in _cleanups) c();
        _cleanups.Clear();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) { _cts?.Cancel(); _cts?.Dispose(); }
        base.Dispose(disposing);
    }

    protected override CreateParams CreateParams
    {
        get { var cp = base.CreateParams; cp.ExStyle |= 0x02000000; return cp; }  // WS_EX_COMPOSITED
    }
}
```

Uso en una pantalla de lista, con el patrón completo de estado + carga + guardas de salida:

```csharp
public sealed class ProductListScreen : ScreenBase, ICacheableScreen
{
    private readonly IProductRepository _repo;
    private readonly INavigationService _nav;
    private ProductListState _state = new();

    public override string Title => "Productos";

    public ProductListScreen(IProductRepository repo, INavigationService nav)
    {
        _repo = repo; _nav = nav;
        InitializeLayout();
    }

    public override async Task OnNavigatedToAsync(NavigationContext ctx)
    {
        _state = ctx.State.GetOrCreate<ProductListState>(nameof(ProductListScreen));
        txtSearch.Text = _state.SearchTerm;
        cboCategory.SelectedValue = _state.CategoryId;
        await LoadAsync();
        txtSearch.Focus();                       // foco correcto al entrar: siempre
        RestoreSelection(_state.SelectedId);
    }

    public override void OnNavigatedFrom(NavigationContext ctx)
    {
        _state.SearchTerm = txtSearch.Text;
        _state.SelectedId = SelectedProductId();
        ctx.State.Set(nameof(ProductListScreen), _state);   // el usuario vuelve y todo sigue igual
        base.OnNavigatedFrom(ctx);
    }

    private void OnRowActivated(int id)
        => _ = _nav.NavigateToAsync<ProductDetailScreen>(id);
}
```

Y la guarda de cambios sin guardar en la pantalla de detalle:

```csharp
public override async Task<bool> CanNavigateAwayAsync()
{
    if (!_model.IsDirty) return true;

    var page = new TaskDialogPage
    {
        Caption = "Cambios sin guardar",
        Heading = "¿Guardar los cambios en este producto?",
        Text = "Si sale sin guardar, los cambios se perderán.",
        Icon = TaskDialogIcon.Warning,
        Buttons = { new TaskDialogButton("Guardar"), new TaskDialogButton("Salir sin guardar"),
                    TaskDialogButton.Cancel }
    };
    var result = TaskDialog.ShowDialog(this, page);

    return result.Text switch
    {
        "Guardar"           => await SaveAsync(),
        "Salir sin guardar" => true,
        _                   => false
    };
}
```

### 15.5 Equivalente en WPF

La misma arquitectura, con menos código, porque el `ContentControl` + `DataTemplate` hace el trabajo:

```xml
<!-- MainShell.xaml -->
<Grid>
    <Grid.ColumnDefinitions>
        <ColumnDefinition Width="240"/>
        <ColumnDefinition Width="*"/>
    </Grid.ColumnDefinitions>
    <Grid.RowDefinitions>
        <RowDefinition Height="40"/>   <!-- identidad -->
        <RowDefinition Height="*"/>
        <RowDefinition Height="24"/>   <!-- estado -->
    </Grid.RowDefinitions>

    <local:IdentityBar Grid.ColumnSpan="2"/>
    <local:NavigationPanel Grid.Row="1"/>

    <!-- La única región que cambia -->
    <ContentControl Grid.Row="1" Grid.Column="1"
                    Content="{Binding CurrentScreen}"
                    Margin="24"/>

    <local:StatusBar Grid.Row="2" Grid.ColumnSpan="2"/>
</Grid>
```

```xml
<!-- App.xaml : mapeo ViewModel -> View. La vista se crea y se destruye sola. -->
<Application.Resources>
    <DataTemplate DataType="{x:Type vm:ProductListViewModel}">
        <views:ProductListView/>
    </DataTemplate>
    <DataTemplate DataType="{x:Type vm:ProductDetailViewModel}">
        <views:ProductDetailView/>
    </DataTemplate>
</Application.Resources>
```

```csharp
// El servicio solo cambia una propiedad; WPF destruye la vista anterior y crea la nueva.
public sealed partial class ShellViewModel : ObservableObject
{
    [ObservableProperty] private ObservableObject? currentScreen;

    public async Task<bool> NavigateToAsync<TVm>(object? parameter = null) where TVm : class
    {
        if (CurrentScreen is IScreen current && !await current.CanNavigateAwayAsync())
            return false;

        (CurrentScreen as IScreen)?.OnNavigatedFrom(ctx);

        var next = _services.GetRequiredService<TVm>() as ObservableObject;
        CurrentScreen = next;                       // ← toda la "reconstrucción" es esta línea

        if (next is IScreen screen) await screen.OnNavigatedToAsync(ctx);
        return true;
    }
}
```

**Nota importante para WPF:** aquí el ViewModel es lo que persiste o se destruye, y la View es puramente visual. Si cacheas ViewModels, la vista se reconstruye igual (barato) y el estado se conserva solo (gratis). Es la separación estado/vista de la sección 10.3 pero incorporada al framework — una de las mejores razones para elegir WPF si el equipo tiene tiempo de aprenderlo.

### 15.6 Helper de layout de formulario (WinForms)

Evita colocar controles a mano y garantiza el espaciado de la escala:

```csharp
public static class FormLayout
{
    /// <summary>Crea la rejilla estándar de formulario: etiquetas a la derecha + campos.</summary>
    public static TableLayoutPanel CreateFieldGrid(int labelWidth = 140)
    {
        var t = new TableLayoutPanel
        {
            ColumnCount = 2,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Dock = DockStyle.Top,
            Padding = Padding.Empty,
            MaximumSize = new Size(Sizes.FormMaxWidth, 0)
        };
        t.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, labelWidth));
        t.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        return t;
    }

    public static void AddField(this TableLayoutPanel grid, string label, Control control, int width = 0)
    {
        var lbl = new Label
        {
            Text = label,
            TextAlign = ContentAlignment.MiddleRight,
            Dock = DockStyle.Fill,
            ForeColor = Theme.Current.TextSecondary,
            Margin = new Padding(0, 0, Space.Sm, Space.Lg)   // 8px al campo, 16px al siguiente
        };
        control.Height = Sizes.ControlHeight;
        control.Margin = new Padding(0, 0, 0, Space.Lg);
        if (width > 0) { control.Width = width; control.Anchor = AnchorStyles.Left | AnchorStyles.Top; }
        else control.Dock = DockStyle.Fill;

        int row = grid.RowCount++;
        grid.Controls.Add(lbl, 0, row);
        grid.Controls.Add(control, 1, row);
    }

    public static Panel CreateGroup(string title, Control content) { /* título SemiBold + 24px abajo */ }
}
```

Uso:

```csharp
var g = FormLayout.CreateFieldGrid();
g.AddField("Código",       txtCodigo,      width: 140);
g.AddField("Descripción",  txtDescripcion);           // ocupa el ancho
g.AddField("Categoría",    cboCategoria,   width: 240);
```

### 15.7 Configuración de grilla estándar (WinForms)

Una sola función que hace que **todas** las grillas del sistema se vean iguales:

```csharp
public static void ApplyStandardStyle(this DataGridView g)
{
    g.EnableHeadersVisualStyles = false;
    g.BorderStyle              = BorderStyle.None;
    g.CellBorderStyle          = DataGridViewCellBorderStyle.SingleHorizontal;  // solo líneas horizontales
    g.GridColor                = Theme.Current.Border;
    g.BackgroundColor          = Theme.Current.SurfaceRaised;
    g.RowHeadersVisible        = false;
    g.AllowUserToAddRows       = false;
    g.AllowUserToResizeRows    = false;
    g.ReadOnly                 = true;
    g.SelectionMode            = DataGridViewSelectionMode.FullRowSelect;
    g.MultiSelect              = false;
    g.RowTemplate.Height       = Sizes.RowHeight;
    g.ColumnHeadersHeight      = Sizes.HeaderRowHeight;
    g.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.EnableResizing;

    g.DefaultCellStyle.Padding          = new Padding(Space.Md, 0, Space.Md, 0);
    g.DefaultCellStyle.SelectionBackColor = Theme.Current.AccentSubtle;
    g.DefaultCellStyle.SelectionForeColor = Theme.Current.TextPrimary;   // NO blanco sobre azul
    g.DefaultCellStyle.ForeColor          = Theme.Current.TextPrimary;
    g.DefaultCellStyle.WrapMode           = DataGridViewTriState.False;

    g.ColumnHeadersDefaultCellStyle.BackColor = Theme.Current.SurfaceSunken;
    g.ColumnHeadersDefaultCellStyle.ForeColor = Theme.Current.TextSecondary;
    g.ColumnHeadersDefaultCellStyle.Font      = Fonts.LabelSemiBold;
    g.ColumnHeadersDefaultCellStyle.Padding   = new Padding(Space.Md, 0, Space.Md, 0);

    // Doble búfer (propiedad protegida): elimina el parpadeo al hacer scroll
    typeof(DataGridView).InvokeMember("DoubleBuffered",
        BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.SetProperty,
        null, g, new object[] { true });
}

public static void AsMoneyColumn(this DataGridViewColumn c)
{
    c.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleRight;
    c.DefaultCellStyle.Format    = "N2";
    c.HeaderCell.Style.Alignment = DataGridViewContentAlignment.MiddleRight;
    c.Width = 140;
}
```

---

## 16. Checklist de QA visual

Pásale esta lista a **cada pantalla** antes de darla por terminada. Es más rápido que rediseñar después y es lo que mantiene la coherencia cuando dos personas desarrollan en paralelo.

### Estructura
- [ ] La pantalla se abre dentro del shell; no es una ventana suelta (salvo modal justificado por la sección 10.7)
- [ ] El título de la pantalla coincide exactamente con el ítem del menú que la abre
- [ ] El ítem del menú lateral queda marcado como activo
- [ ] La pantalla corresponde a uno de los 5 arquetipos y respeta su estructura
- [ ] El cromo permanente ocupa ≤ 220 px de alto en 1366×768

### Espacio y alineación
- [ ] Todos los espacios son valores de la escala (4/8/12/16/24/32/48)
- [ ] El espacio entre grupos es al menos el doble que el espacio entre campos del mismo grupo
- [ ] Margen exterior del cuerpo = 24 px en los cuatro lados
- [ ] Los controles están alineados en una rejilla; no hay bordes izquierdos desalineados por 2–3 px
- [ ] El ancho de cada campo corresponde a la longitud esperada del dato (no todo estirado al 100%)
- [ ] El área de formulario no supera ~760 px de ancho
- [ ] No hay más de 2 niveles de contenedor con borde anidados

### Tipografía y color
- [ ] Una sola familia tipográfica; máximo 4 tamaños en la pantalla
- [ ] Ningún color escrito literal en el código: todo sale de los tokens de rol
- [ ] **Un solo** botón con color de acento
- [ ] Ningún estado se comunica solo con color (siempre color + texto)
- [ ] Contraste de texto ≥ 4.5:1 verificado con herramienta
- [ ] El color ocupa ≤ 10% de la superficie de la pantalla

### Datos
- [ ] Números y montos alineados a la derecha, formato `N2` con separador de miles
- [ ] Encabezados alineados igual que su contenido
- [ ] ≤ 9 columnas visibles; la columna descriptiva absorbe el ancho sobrante
- [ ] Encabezado de grilla congelado al hacer scroll
- [ ] Filas de altura uniforme, sin ajuste de línea, con tooltip en texto truncado

### Estados
- [ ] Estado **cargando** diseñado y probado (con la BD lenta a propósito)
- [ ] Estado **vacío inicial** con mensaje y acción
- [ ] Estado **vacío por filtro**, con texto distinto al anterior y opción de limpiar filtros
- [ ] Estado **error** con explicación en español claro, botón de reintentar y detalle técnico colapsable
- [ ] Ninguna operación > 300 ms ocurre sin indicador visible
- [ ] Ninguna operación bloquea la UI (todo `async`)

### Interacción
- [ ] El foco inicial está en el control correcto
- [ ] El orden de tabulación sigue el orden visual (revisado control por control)
- [ ] `Esc` y `Enter` hacen lo esperado
- [ ] El flujo completo se puede ejecutar **sin mouse**
- [ ] Los atajos de teclado están visibles en los botones que los tienen
- [ ] Al volver desde el detalle, la lista conserva filtros, página, scroll y fila seleccionada
- [ ] Salir con cambios sin guardar pide confirmación (y la confirmación ofrece guardar)
- [ ] Al cerrar un modal, el foco vuelve al control que lo abrió

### Técnico
- [ ] Se ve correctamente en 1366×768 sin scroll horizontal
- [ ] Se ve correctamente a 100%, 125% y 150% de escala DPI
- [ ] Sin parpadeo al cargar datos o al cambiar de pantalla
- [ ] Navegar 30 veces entrando y saliendo de la pantalla no incrementa memoria ni objetos GDI/User
- [ ] Todos los eventos suscritos a objetos de vida larga se desuscriben al salir
- [ ] Todos los modales se abren con `using` / se liberan

---

## 17. Anti-patrones que matan sistemas empresariales

| Anti-patrón | Por qué duele | Qué hacer |
|---|---|---|
| Una `Form` por cada pantalla, abiertas todas a la vez | El usuario pierde ventanas, no sabe cuál está activa, duplica registros | Shell + `UserControl` (sección 10) |
| `public static FrmX Instancia` | Estado sucio, datos obsoletos, fugas | Contenedor DI + `ViewState` |
| Perder los filtros de la lista al volver del detalle | Rehacer la búsqueda 200 veces al día | `ViewState` persistido |
| `MessageBox` por cada guardado exitoso | 200 clics extra diarios; entrena a ignorar los diálogos | Banner efímero |
| Mostrar `SqlException.Message` al usuario | Nadie entiende, nadie puede actuar | Mensaje traducido + detalle colapsable |
| `AutoSizeColumnsMode = Fill` en todas las columnas | Columnas numéricas de 300 px; tabla que se ve vacía y desordenada | `Fill` solo en la columna descriptiva |
| Rejilla completa estilo Excel + zebra + bordes 3D | Ruido visual; se ve de 1998 | Solo líneas horizontales sutiles |
| Todo el formulario estirado al 100% del ancho | Se ve desordenado y obliga a barrer la vista | Ancho por tipo de dato; máximo 760 px |
| Color de marca en el fondo de barras, encabezados y botones | Se pierde la jerarquía; nada destaca | Acento solo en la acción primaria |
| Llamadas síncronas a SP pesados | "No responde", el usuario mata el proceso | `async` + `CancellationToken` + indicador |
| Posiciones absolutas de controles | Se rompe a 125%/150% DPI | `TableLayoutPanel` / `Grid` |
| `Application.DoEvents()` | Reentrada, bugs irreproducibles | `async/await` |
| Modal encima de modal | El usuario se pierde; `Esc` cierra el equivocado | Rediseñar el flujo |
| Iconos sin texto en la navegación | El usuario no sabe qué es cada uno; nadie descubre módulos | Icono + texto siempre (colapsado: tooltip) |
| Cachear la vista y no recargar los datos | Inventario desactualizado en sistema multiusuario | Recargar siempre en `OnNavigatedToAsync` |

---

## 18. Fuentes

- Nielsen Norman Group — [8 Design Guidelines for Complex Applications](https://www.nngroup.com/articles/complex-application-design/)
- Nielsen Norman Group — [10 Usability Heuristics Applied to Complex Applications](https://www.nngroup.com/articles/usability-heuristics-complex-applications/)
- Microsoft — [Fluent 2 Design System: Layout (escala de espaciado 4 px)](https://fluent2.microsoft.design/layout)
- Microsoft Learn — [What's new in WinForms for .NET 10 (modo oscuro estable, `SetColorMode`, formularios async)](https://learn.microsoft.com/en-us/dotnet/desktop/winforms/whats-new/net100)
- Microsoft Learn — [WPF Tips and Tricks: Using ContentControl instead of Frame and Page for Navigation](https://learn.microsoft.com/ko-kr/archive/technet-wiki/52485.wpf-tips-and-tricks-using-contentcontrol-instead-of-frame-and-page-for-navigation)
- Pencil & Paper — [UX Pattern Analysis: Enterprise Data Tables](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables)
- Setproduct — [Data table UI design reference guide 2026](https://www.setproduct.com/blog/data-table-ui-design)
