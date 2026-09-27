# Investigación y plan de mejora de UI/UX — SistemasHN

Fecha: 2026-09-27 · Rama: `desarrollo` · Alcance: estructura de pantallas, navegación, flujos, jerarquía de información, consistencia y velocidad en el mostrador. **Fuera de alcance: la paleta Grafito y Vino, que se mantiene tal cual (`core/ui/theme.py`), y el stack (sigue siendo Flet 1.0).**

## 1. Resumen ejecutivo

El sistema tiene ~20 pantallas funcionales, construidas pantalla por pantalla con widgets comunes mínimos (`core/ui/widgets.py`). La base es correcta: permisos en menú y servicio, estados vacíos y mensajes de error. Pero la UI está pensada como formulario administrativo, no como mostrador. Hay cinco problemas de fondo:

- El orden del menú y la pantalla de inicio ignoran el perfil de quien entra.
- El POS pierde la venta si el cajero navega a otra pantalla.
- El POS no tiene foco automático, atajos ni búsqueda por nombre, y obliga a varios clics para una venta al contado.
- La captura de líneas y pagos está copiada tres veces y ya diverge.
- Los historiales muestran ids y fechas UTC en lugar de nombres y hora local.

El plan corrige primero los errores que hacen perder trabajo o mostrar datos equivocados (P0). Después propone un "modo mostrador" y componentes compartidos de captura (P1), sin controles de Flet que no existan en la 1.0.0 instalada.

## 2. Estado actual (lo que hay en el código)

### 2.1 Infraestructura compartida
- **Tema** (`core/ui/theme.py`): tokens de color, `SPACING` (4–24) y `RADIUS=8`. Material 3 sembrado con `PRIMARY`. Ventana mínima 1024×640 en `theme.py:57-58`, que `app_shell.py:67-68` sobrescribe a 1024×700. Hay dos valores distintos para lo mismo.
- **Widgets** (`core/ui/widgets.py`): `page_header`, `empty_state`, `error_banner`, `loading`, `confirm_dialog`, `paginated_table` (DataTable + anterior/siguiente), `form_field`, `primary_button` (FilledButton), `secondary_button` (OutlinedButton), `file_picker` e `image_picker`. **No hay** widget de éxito (banner o snackbar), de "campo de dinero", de "selector de contraparte", de "captura de líneas" ni de "captura de pagos".
- **Barra lateral** (`core/ui/shell.py:45-123`): ancho fijo de 240 px. Agrupa con `groupby` por `screen.group` y muestra al pie el usuario y "Cerrar sesión". El contenido va dentro de un `Column(scroll=AUTO)` (`shell.py:140-149`). No hay cabecera superior con estado de caja, usuario ni fecha.
- **Router** (`core/ui/router.py`): `visible_screens()` abre **una sesión de BD por pantalla** para comprobar permisos (`router.py:34-40`), unas 22 consultas en cada navegación y en cada error. Ordena por `(group, order)`, es decir, **alfabético por nombre de grupo** (`router.py:52`; también `core/modules/contracts.py:91`).
- **Composición** (`core/ui/app_shell.py`):
  - `_render()` reconstruye la página completa en cada navegación (`app_shell.py:90-101`, `144-148`).
  - La ruta inicial es `visibles[0]` (`app_shell.py:111-112`).
  - Los errores de servicio se muestran como banner encima de todo (`app_shell.py:117-122`).

### 2.2 Menú completo (22 rutas declaradas)

Grupos en el orden en que aparecen hoy (alfabético):

| Grupo | Rutas (permiso) |
|---|---|
| Administración | Usuarios, Auditoría, Ajustes, Respaldos, Licencia (`core.*`) |
| Catálogo | Catálogo (`com.catalogo.ver`), Importar catálogo (`com.catalogo.importar`) |
| Compras | Contrapartes (`com.contrapartes.ver`), Compras, Nueva compra, Cuentas por pagar |
| Inventario | Inventario, Stock bajo (`com.inventario.ver`) |
| Repuestos | Vehículos (`rep.vehiculos.gestionar`), Buscar por vehículo (`com.catalogo.ver`) |
| Reportes | Reportes (`com.reportes.ver`), **sin builder aún** |
| Ventas | Punto de venta, Cotizaciones, Ventas, Caja, Cuentas por cobrar, Devoluciones (**sin builder aún**) |

- **Vendedor** (`comercial/module.py:40-58`): ve Catálogo, Inventario, Stock bajo, Buscar por vehículo, POS, Cotizaciones, Ventas, Caja y CxC (Devoluciones cuando exista). Aterriza en **Catálogo**; el POS es el 5.º elemento.
- **Administrador/gerente**: ve las ~20 rutas y aterriza en **Usuarios**.
- **Bodega**: aterriza en Catálogo, que para ese perfil es lo correcto.

### 2.3 Pantallas revisadas

- **POS** (`comercial/ui/pos_view.py`): una sola columna con scroll. De arriba abajo: aviso de caja, búsqueda de cliente (Enter o botón, resultados como botones), código y cantidad (Enter agrega), lista de líneas como texto `código - nombre · cant · precio` con botón de quitar, bloque de pagos (dropdown de método, monto, referencia y "Agregar pago"), vencimiento de crédito como texto `AAAA-MM-DD`, totales, error y éxito, y "Confirmar venta" al final (`pos_view.py:382-425`).
  - Estado local en `estado` (`pos_view.py:58-64`).
  - Sin `autofocus` ni `.focus()`.
  - Si ya existe la línea, la reemplaza (`pos_view.py:200`).
  - Sin pagos = crédito, que exige cliente y fecha (`pos_view.py:327-342`).
  - Muestra el vuelto calculado en vivo (`pos_view.py:149-166`).
  - Botón de factura fiscal deshabilitado cuando aplica (`pos_view.py:426-437`).
- **Nueva compra** (`compras_view.py:171-568`): mismo esqueleto con proveedor obligatorio y referencia de factura.
  - Enter en el código **solo** sugiere costo (`compras_view.py:373`); hay que pulsar "Agregar línea" (`:539`).
  - La etiqueta dice "Último costo con este proveedor" (`:368`), pero `last_prices` no filtra por proveedor (`compras/service.py:371-380`).
  - La sugerencia no rellena el campo de costo.
  - La cantidad no tiene valor por defecto; en el POS es "1".
- **Historial de compras** (`compras_view.py:33-151`): búsqueda por número o proveedor (Enter) y detalle en diálogo de solo lectura. Fecha `purchased_at.date()` en UTC (`:82`). Sin anular aunque existe `PurchaseService.void`.
- **Cotizaciones** (`cotizaciones_view.py`):
  - Lista con filtro de estado; la búsqueda **solo por número**.
  - Columna Cliente muestra `customer_id` (`:146`).
  - No hay detalle de la cotización: no se pueden ver sus líneas.
  - "Nueva cotización" es un **diálogo** de 520×560 (`:301-303`) con el mismo patrón de líneas pero **sin** Enter para agregar. Vigencia como texto obligatorio sin valor por defecto (`:177`).
  - La conversión a venta es otro diálogo (`:389-570`): el monto viene prellenado con el total, pero hay que pulsar "Agregar pago"; si se pulsa "Convertir" directamente, `payments=[]`. **No pasa `cash_session_id`** (`:491-504`). Las diferencias se muestran como `producto {id}` (`:517`). Al terminar, no informa número de venta ni vuelto (`:537-538`).
  - "Convertir a venta" aparece sin comprobar `com.ventas.registrar` (`:96-101`).
- **Caja** (`caja_view.py`):
  - Abrir, entradas y salidas manuales y cierre con conciliación esperado/contado/diferencia (bien resuelto, `:145-152`).
  - Fechas en `isoformat()` crudo (`:181`, `:239-240`), cuando existe `format_local_datetime`.
  - Tipos de movimiento como código interno (`:213`).
  - El vendedor tiene `caja.operar` pero no `caja.cerrar`.
- **CxC / CxP** (`cxc_view.py`, `cxp_view.py`): duplicados a propósito (docstring `cxc_view.py:3-5`).
  - Filtro por estado con color (vencida en rojo) y abono en diálogo con saldo en la etiqueta.
  - Origen `"{source_type} #{source_id}"` (`cxc_view.py:163`).
  - Sin total adeudado, sin historial de abonos y sin ligar el efectivo a la caja.
- **Contrapartes** (`contrapartes_view.py`):
  - Búsqueda con debounce de 300 ms (hilo `threading.Timer`).
  - Aviso de duplicados con "Crear de todos modos".
  - Está en el grupo "Compras" aunque también contiene clientes.
  - El vendedor no tiene acceso.
- **Ventas** (`ventas_view.py`): solo lectura; búsqueda **solo por número**; cliente como id (`:62`); fecha UTC (`:63`). El detalle en diálogo sangra bien los componentes de kit (`:80-87`). Sin anular ni reimprimir.
- **Catálogo** (`catalog_view.py`):
  - Búsqueda con debounce; Enter abre el producto si hay coincidencia exacta (`:82-95`), buen patrón.
  - Diálogo de producto de 520×560 que mezcla datos, existencias, movimientos, ajuste, kit y la extensión de Repuestos. Tiene dos botones primarios: "Guardar" y "Guardar composición".
  - "Composición guardada." en color de error (`:440`).
  - `list_categories` se llama en cada render (`:177`).
- **Inventario** (`inventory_view.py`): solo búsqueda exacta por código (`:39`).
- **Buscar por vehículo** (`repuestos/ui/compatible_view.py`): resultados solo con código y nombre (`:79`). Sin precio ni disponible, y sin forma de llevar el producto a la venta: es un callejón sin salida para el mostrador.
- **Devoluciones / Reportes**: `devoluciones_view.py` y `reportes_view.py` **no existen** todavía (T5.6 pendiente en `docs/validation/progreso.md`; hay pruebas nuevas sin rastrear en `tests/comercial/ui/`). No los revisé.
- **Documentos PDF**: el servicio existe (`comercial/documentos/`, T5.4), pero ninguna pantalla ofrece imprimir o guardar PDF.

### 2.4 Capacidades de Flet 1.0.0

Verificado en `evn/lib/python3.14/site-packages/flet`. ADR-004 solo documenta cambios de nombres de la API. En la versión instalada existen, aunque el repo no los usa:
- `Page.on_keyboard_event` con `KeyboardEvent(key, shift, ctrl, alt, meta)` (`controls/page.py:265`).
- `TextField.focus()` asíncrono (`form_field_control.py:563`).
- `SnackBar` y `DatePicker`, que son `DialogControl` y se muestran con `page.show_dialog`.
- `Tabs`, `NavigationRail`, `AutoComplete`, `SearchBar`, `ExpansionTile`, `KeyboardListener`, `MenuBar` y `PopupMenuButton`.

Ninguno aparece en el código (grep: cero usos de `on_keyboard_event`, `.focus()`, `SnackBar`, `DatePicker`). La docstring de `compras_view.py:175` evitó `DatePicker` a propósito ("no usado en el repo"). **Recomendación:** hacer una prueba técnica corta en Windows (foco tras `on_submit`, F-keys globales mientras un TextField tiene foco, `DatePicker` y `SnackBar`) y registrar el resultado como anexo de ADR-004 antes de depender de ellos.

## 3. Diagnóstico priorizado

### P0 — Pérdida de trabajo, datos equivocados o dinero mal registrado
1. **La venta en curso se pierde al navegar** (`app_shell.py:144-148` + `pos_view.py:58`). Pasa también con una compra a medio capturar.
2. **Escanear dos veces el mismo producto no suma**: deja cantidad 1 (`pos_view.py:200`; igual en compras `:327` y cotizaciones `:282`). Con lector de código de barras es el error más probable en caja.
3. **Ids en lugar de nombres**: cliente en Cotizaciones y Ventas, producto en las diferencias de conversión, origen en CxC y CxP.
4. **Fechas UTC o ISO crudas** en Ventas, Compras y Caja, cuando existe `format_local_datetime` (Honduras). Una venta nocturna aparece con fecha del día siguiente.
5. **La conversión de cotización no liga el efectivo a la caja** ni muestra el vuelto. Además, si no se pulsa "Agregar pago" antes de "Convertir", los pagos quedan vacíos y la venta termina en crédito o en error. El POS permite vender sin caja abierta con solo un texto rojo de aviso (`pos_view.py:99`). Hay que decidir con el dueño si se bloquea.
6. **Mensaje de éxito en color de error** (`catalog_view.py:440`) y **etiqueta engañosa de costo sugerido** (`compras_view.py:368`).
7. **El vendedor no puede registrar un cliente nuevo**, porque las contrapartes requieren permisos que su perfil no tiene. Una venta a crédito a un cliente nuevo exige llamar al gerente. Es una decisión de producto, pero hoy es un callejón sin salida.

### P1 — Velocidad y claridad en el mostrador
8. **Navegación no orientada al rol**: el POS queda al fondo del menú, la pantalla de inicio no es la de trabajo y hay 9–20 elementos siempre visibles. "Contrapartes" es jerga y está en el grupo "Compras".
9. **El POS no está hecho para teclado ni lector**:
   - Sin foco inicial ni retorno del foco al campo de código.
   - Sin atajos.
   - Enter en el monto no agrega el pago.
   - Sin botón de "pago exacto".
   - Sin búsqueda por nombre, número de parte o equivalencia (la spec §4 la exige).
   - Sin existencias visibles al agregar.
   - La cantidad solo se cambia quitando la línea y volviendo a agregarla.
10. **Jerarquía visual del POS**: el total, el vuelto y el botón de confirmar están al final del scroll con el mismo tamaño de texto que el resto. En 1366×768 (típico en hardware modesto), con pocas líneas ya quedan fuera de la vista. Los mensajes de error y éxito aparecen abajo, lejos de donde el usuario mira.
11. **Tres implementaciones divergentes del mismo patrón** (líneas + contraparte + pagos + vencimiento):

| Aspecto | POS | Compra | Cotización |
|---|---|---|---|
| Contenedor | pantalla completa | ruta aparte ("Nueva compra") | diálogo de 520 px |
| Enter en el código | agrega | solo sugiere costo | nada |
| Cantidad por defecto | 1 | vacía | vacía |
| Producto repetido | reemplaza | reemplaza | reemplaza |
| Pagos | sí | sí | no (en la conversión, diálogo aparte) |
| Fecha | texto | texto | texto |

    Cada corrección hay que hacerla tres veces (cuatro con la sección de kits del catálogo).
12. **"Buscar por vehículo" sin continuación**: no muestra precio ni existencias y no permite "agregar a la venta".

### P2 — Historiales, retroalimentación y pulido
13. Historiales (Ventas, Cotizaciones, Compras) solo buscan por número, sin filtro por fecha ni por cliente. No hay acciones sobre el documento (reimprimir, anular) aunque los servicios existen. La cotización no tiene vista de detalle.
14. No hay un patrón de éxito consistente: texto verde abajo en POS y compras, cierre silencioso del diálogo en cotizaciones y abonos, texto rojo en kits.
15. Caja: el estado de la caja solo se ve entrando a "Caja". Los tipos de movimiento aparecen como códigos internos y el cierre no desglosa por método de pago.
16. El diálogo de producto está sobrecargado (datos + existencias + movimientos + ajuste + kit + repuestos en 560 px de alto) y tiene dos acciones primarias.
17. Sensación de lentitud en HDD: cada navegación hace ~22 consultas de permisos más las de `tiene_permiso` de la pantalla, y reconstruye la barra lateral completa.
18. La ventana mínima se define en dos sitios con valores distintos (640 y 700). No hay pruebas de escalado de Windows al 125 %/150 %, que la spec §6 exige.

## 4. Plan de mejora propuesto

Solo incluye decisiones técnicas o de consistencia que se pueden tomar sin el dueño. Lo que depende de él está marcado como **[pregunta X]**.

### Fase P0 — Correcciones sin cambio de diseño (bajo riesgo)
- **P0.1 Conservar el estado del POS y de la nueva compra entre navegaciones.** Guardar en `DesktopApp` una caché del control construido por ruta, al menos para `/pos` y `/compras/nueva`, o sacar el `estado` a `ctx`. Si hay líneas capturadas y se intenta salir, pedir confirmación "Tiene una venta sin confirmar" con `widgets.confirm_dialog`. **[pregunta D9]**
- **P0.2 El producto repetido suma cantidad** en POS, compra y cotización. **[pregunta D5]** por si el dueño prefiere una línea por escaneo.
- **P0.3 Nombres en lugar de ids.** Añadir `customer_name` a `SaleSummary`/`QuoteSummary` o resolverlo en la vista. Mostrar el número de documento en CxC y CxP ("Venta V-000123"). Mostrar el código y nombre del producto en las diferencias de conversión.
- **P0.4 Fechas siempre con `format_local_datetime`**, o con una variante solo de fecha a añadir en `core/ui/views`, en todas las tablas y detalles.
- **P0.5 La conversión de cotización pasa `cash_session_id`**, muestra el vuelto y el número de venta al terminar, y trata el monto prellenado como pago implícito si la lista de pagos está vacía.
- **P0.6** Mostrar "Composición guardada." en color de éxito. Corregir la etiqueta del costo sugerido, o filtrar por proveedor en el servicio, y usar la sugerencia como valor inicial del campo de costo.
- **P0.7 Unificar la ventana mínima** en `theme.apply_page_theme`.

### Fase P1a — Navegación orientada al rol
- **Orden explícito de grupos.** Añadir `group_order` a `ScreenDef` o un mapa central de orden en lugar del orden alfabético. Orden propuesto: Ventas → Catálogo/Inventario → Compras → Repuestos → Reportes → Administración. **[pregunta C6]**
- **Pantalla de inicio por perfil.** El vendedor aterriza en el POS, bodega en Catálogo y el gerente en un resumen o en Reportes. Técnicamente basta con la primera ruta visible después de reordenar, o con un campo `home_route` en el perfil. **[preguntas C1, C7]**
- **Renombrar "Contrapartes"** a "Clientes y proveedores" y sacarla del grupo Compras. **[pregunta E3]**
- **Barra superior fina en el área de contenido**, con usuario, estado de caja (por ejemplo "Caja abierta · 08:02" o "Sin caja abierta" con acceso directo) y fecha. Se ve desde todas las pantallas.
- **Caché de permisos** por sesión de usuario: un único `authorizer` para todas las pantallas al entrar, que se invalida al cerrar sesión o al cambiar permisos.
- Mantener la barra lateral de Flet actual en lugar de migrar a `NavigationRail`, que no aporta nada con ~10 ítems por perfil. Evaluar grupos plegables (`ExpansionTile`) solo para Administración.

### Fase P1b — Modo mostrador (POS)
Rediseño de la pantalla `/pos` sin nuevas dependencias:
- **Diseño en dos columnas** que ocupe el alto disponible sin scroll general:
  - **Izquierda**: campo de código grande con foco permanente y, debajo, tabla de líneas (DataTable con Código, Descripción, Cant., Precio, Total y Quitar; la cantidad editable con clic o con +/−).
  - **Derecha, fija**: cliente (compacto), **TOTAL en tipografía grande**, pagos, vuelto y crédito destacados, y el botón primario "Cobrar" siempre visible. Los errores aparecen junto al campo que los causa o arriba del panel derecho, no al final.
- **Foco**: `autofocus` en el código. Después de agregar, quitar, cobrar o cerrar un diálogo, llamar `await campo.focus()`, sujeto a la prueba técnica.
- **Búsqueda por nombre**: si lo escrito no coincide exactamente con un código, abrir un diálogo con resultados de `catalog.search` (paginado, 10–20 filas) con precio y disponible. Enter o doble clic agrega. Después, extender a número de parte y equivalencia vía Repuestos. **[pregunta D2]**
- **Cobro rápido**: botones "Efectivo exacto", "Tarjeta por el total" y "Transferencia por el total". Enter en el monto agrega el pago. El monto se prellena con el saldo pendiente.
- **Crédito**: el vencimiento se prellena con un plazo por defecto y se puede cambiar con `DatePicker`, con texto como alternativa si la prueba técnica falla. **[preguntas F1, F2]**
- **Atajos de teclado** (`page.on_keyboard_event`, solo teclas F para no chocar con la escritura). Propuesta inicial, **[pregunta D10]**:
  - F2: buscar producto.
  - F3: buscar cliente.
  - F4: cambiar cantidad de la última línea.
  - F8: agregar pago.
  - F12: cobrar.
  - Esc: cerrar diálogo o volver al código.
  - Ctrl+N: nueva venta.
  Mostrarlos en la pantalla junto a cada botón ("Cobrar (F12)").
- **Tras cobrar**: diálogo o panel de resultado con número de venta, **vuelto en grande** y los botones "Imprimir comprobante" (cuando exista la UI de documentos; T5.4 ya da el PDF) y "Nueva venta (Enter)". **[preguntas D3, D7, B6]**
- **Caja**: si no hay caja abierta al entrar al POS, ofrecer abrirla ahí mismo. Bloquear o solo avisar según **[pregunta D12]**.
- **"Buscar por vehículo"**: añadir precio, disponible y un botón "Agregar a la venta", que manda el producto al POS en curso gracias a P0.1.
- **Opcional** **[preguntas C2–C5]**: ocultar la barra lateral en el POS para ganar ~240 px, con un botón para mostrarla.

### Fase P1c — Componentes compartidos de captura
Crear en `comercial/ui/` (por ejemplo `capture.py`) tres componentes que usen POS, compra, cotización y conversión:
- `PartyPicker(role)`: búsqueda con Enter, resultados en una lista compacta, "✕ quitar" y, si hay permiso, "+ Nuevo". **[pregunta E1]**
- `LineCapture(price_source=sale_price|cost, allow_cost_edit, on_change)`: Enter agrega, cantidad por defecto 1, un producto repetido suma, tabla editable y búsqueda por nombre integrada.
- `PaymentCapture(total, allow_credit, cash_session)`: botones de pago exacto, Enter para agregar, saldo, vuelto y crédito.

Regla de contenedor: todo flujo con **más de una sección de captura va en pantalla completa**; los diálogos quedan para ediciones de una sola sección (abonos, apertura de caja, ajuste). Consecuencias:
- "Nueva cotización" pasa a pantalla completa, idéntica al POS pero con "Guardar cotización" en lugar de "Cobrar", más vigencia y apartado. **[pregunta H1]**
- "Convertir a venta" carga la cotización en el POS ya poblada: una sola pantalla de cobro.
- Con el patrón unificado, un cambio se hace una sola vez.

### Fase P2 — Historiales, retroalimentación y pulido
- **Historiales**:
  - Búsqueda unificada (número, cliente o proveedor) y filtro rápido de fecha (Hoy, Ayer, Esta semana, rango con `DatePicker`).
  - El detalle muestra acciones según permisos: Reimprimir, Anular con motivo (`SaleService.void`, `PurchaseService.void`) y, en cotizaciones, "Ver líneas" antes de convertir.
  - "Ver venta" desde CxC.
- **Retroalimentación**:
  - Éxito: `SnackBar` o un banner verde consistente arriba del contenido, con un widget nuevo `success_banner` junto a `error_banner`.
  - Error: siempre visible sin hacer scroll.
  - Acciones de dinero irreversibles (anular, cerrar caja): `confirm_dialog` con el resumen del monto.
- **Caja**: movimientos con etiquetas legibles y hora local; cierre con desglose por método de pago y la opción de imprimir el cierre.
- **Diálogo de producto**: separar en `Tabs` (Datos, Existencias y movimientos, Kit, Repuestos) con una sola acción primaria por pestaña.
- **CxC/CxP**: total adeudado arriba, filtro de "vencidas" de un clic e historial de abonos por cuenta.
- **Escalado**: probar a 100/125/150 % en 1366×768 y en el monitor real del mostrador. Documentarlo en `docs/validation/`.
- **Consistencia menor**: estados legibles en lugar de `status.capitalize()` de un código, y mensajes de error con mayúscula inicial.

### Secuencia y dependencias
1. P0 (independiente; corregir y probar ya).
2. Prueba técnica de foco, teclado, `DatePicker` y `SnackBar`, y anexo a ADR-004.
3. P1c (componentes).
4. P1b (POS sobre los componentes).
5. P1a (navegación; puede ir en paralelo con 3–4).
6. P2, coordinado con T5.6 (Devoluciones y Reportes deben nacer ya con los patrones nuevos).

**Pruebas**: las pruebas de UI existentes (`tests/comercial/ui/`) cubren builders y comportamiento. Al unificar componentes hay que migrarlas. P0.2 y P0.5 cambian el comportamiento esperado por algunas pruebas.

> **Pendiente de esta versión del documento**: falta la sección de referencias de otros sistemas
> (SAP Business One, Odoo, POS de mostrador tipo Square/Loyverse) pedida explícitamente por el
> dueño, que se agregará en una siguiente pasada del mismo agente de investigación citando qué
> sistema inspiró cada recomendación concreta (no se afirma nada sobre esos sistemas sin
> verificarlo primero).

## 5. Preguntas abiertas para el dueño del negocio

### A. Personas y hábitos
- A1. En un turno normal, ¿cuántas personas usan la PC y en qué roles (solo cajero, vendedor que cobra, bodeguero que también vende)?
- A2. ¿La misma persona atiende al cliente, busca la pieza y cobra, o hay alguien que despacha y otro que cobra?
- A3. ¿Qué tan cómodos son sus empleados con la computadora: escriben rápido, usan el teclado o dependen del mouse? ¿Alguno tiene dificultad para leer letra pequeña?
- A4. ¿Los empleados rotan con frecuencia? ¿Cuánto tiempo puede dedicar a enseñarle el sistema a alguien nuevo?
- A5. ¿Cada empleado inicia sesión con su propio usuario al empezar su turno, o prefieren una sesión compartida? ¿Cambiar de usuario cuando otro va a cobrar le parece aceptable?
- A6. ¿Usted (el dueño) también cobra en el mostrador, o solo revisa reportes y administra?

### B. Equipo físico en el mostrador
- B1. ¿Tamaño y resolución del monitor del mostrador (por ejemplo 19" 1366×768, 22" 1920×1080)? ¿Tiene Windows con escalado al 125 % o más?
- B2. ¿La PC está en el mostrador, de cara al cliente o en otro lugar?
- B3. ¿Tiene o piensa tener lector de código de barras? ¿Cuántos de sus productos tienen código de barras hoy (casi todos, la mitad, pocos)?
- B4. ¿Usan pantalla táctil? ¿Hay mouse y teclado completo, con teclado numérico?
- B5. ¿Tiene impresora térmica (58 u 80 mm), impresora de carta, ambas o ninguna?
- B6. ¿Imprime comprobante en todas las ventas, solo si el cliente lo pide o nunca?
- B7. ¿Usa gaveta de dinero que se abra con la impresora?
- B8. ¿Hay una segunda pantalla o una pantalla visible para el cliente?

### C. Estructura de navegación
- C1. Cuando un cajero inicia sesión, ¿quiere que el sistema abra directamente el Punto de venta?
- C2. ¿Prefiere un "modo mostrador" sin la barra lateral (solo POS, con botones para Caja, Buscar por vehículo y Cotizaciones), o que el cajero vea el menú normal?
- C3. Si existe ese modo, ¿debe poder salir el cajero por su cuenta o solo con clave de gerente?
- C4. ¿El vendedor debe ver Catálogo, Inventario y Stock bajo en su menú, o le basta con consultar precio y existencias desde el POS?
- C5. ¿Hay pantallas que quiere ocultar a todos porque no las usará (por ejemplo "Importar catálogo" después de la carga inicial, o "Licencia")?
- C6. ¿En qué orden quiere los grupos del menú? Propuesta: Ventas, Catálogo/Inventario, Compras, Repuestos, Reportes, Administración.
- C7. Al entrar usted como gerente o dueño, ¿qué quiere ver primero: ventas del día, caja actual, stock bajo, cuentas por cobrar vencidas u otra cosa?
- C8. ¿Le molesta que ciertas pantallas se abran en ventana emergente (diálogos) o prefiere que todo sea pantalla completa?

### D. Flujo de venta en el mostrador
- D1. ¿Cuántas ventas hace en un día normal y en un día pico? ¿Cuántas piezas lleva una venta típica?
- D2. Cuando el cliente pide una pieza, ¿cómo la buscan: por código interno, por número de parte del fabricante, por nombre ("filtro de aceite Corolla") o por vehículo (marca, modelo, año)? Ordénelas por frecuencia.
- D3. Antes de confirmar, ¿quiere ver un resumen y pulsar "Confirmar" otra vez, o que la venta se registre en cuanto se cobre, lo más rápido posible?
- D4. ¿El cajero puede cambiar el precio de venta de una línea (descuento o regateo)? ¿Con qué límite? ¿Necesita autorización del gerente?
- D5. Si se escanea dos veces la misma pieza, ¿debe sumar a la misma línea (cantidad 2) o crear dos líneas?
- D6. ¿Se venden cantidades fraccionarias en el mostrador (metros de cable, litros de aceite)? ¿Cómo se capturan hoy?
- D7. Después de una venta, ¿qué es lo más importante que el cajero vea: el vuelto, el número de comprobante o el total?
- D8. ¿Es común que una venta quede "en espera" (el cliente fue por algo más) mientras se atiende a otro? ¿Necesita varias ventas abiertas a la vez?
- D9. Si el cajero sale del POS con una venta a medias, ¿debe conservarse la venta, preguntar o descartarse?
- D10. ¿Sus empleados están acostumbrados a teclas de función (F2, F12…) de otro sistema? ¿Cuáles usaban?
- D11. En la mayoría de ventas, ¿el cliente queda anónimo ("consumidor final") o se registra su nombre/RTN?
- D12. ¿Debe el sistema **impedir** vender si no hay caja abierta, o solo avisar? Hoy permite vender y el efectivo no queda en ninguna caja.
- D13. ¿Quiere que el sistema pida confirmación antes de vender una pieza sin existencias suficientes, o que lo impida?
- D14. ¿Qué tan común es el pago mixto (parte efectivo y parte tarjeta o transferencia)? ¿Para las transferencias piden número de referencia siempre?
- D15. ¿Aceptan dólares u otra moneda en el mostrador?

### E. Clientes y crédito
- E1. ¿El cajero o vendedor debe poder **registrar un cliente nuevo** desde el POS? Hoy su perfil no puede.
- E2. ¿Quién autoriza una venta a crédito: cualquier vendedor o solo el gerente? ¿Hay límite de crédito por cliente?
- E3. ¿Cómo llama usted a clientes y proveedores en conjunto? ("Contrapartes" es el término interno.)
- E4. ¿Le interesa ver al elegir un cliente su saldo pendiente o si tiene cuentas vencidas?
- E5. ¿Cómo cobra hoy los abonos: en el mostrador con el cliente presente o por transferencia que luego registra alguien?
- E6. ¿Necesita imprimir un estado de cuenta o un recibo de abono para el cliente?

### F. Fechas y plazos
- F1. ¿Cuál es el plazo de crédito habitual (15, 30 días…)? ¿Varía por cliente?
- F2. ¿Prefiere elegir fechas en un calendario o escribirlas? ¿En qué formato las escriben sus empleados (dd/mm/aaaa)?
- F3. ¿Cuántos días de vigencia suele dar a una cotización?

### G. Devoluciones y anulaciones (cómo funciona hoy en el mostrador, fuera del sistema)
- G1. Hoy, cuando un cliente devuelve una pieza, ¿qué pasa exactamente: le devuelve el dinero, le cambia la pieza o le deja saldo a favor? ¿Cuál es lo más común?
- G2. ¿Quién puede aceptar una devolución: cualquier vendedor o solo el gerente?
- G3. ¿Exige el comprobante original? ¿Cómo encuentra la venta original: por número, por cliente o por fecha aproximada?
- G4. ¿Con qué frecuencia se devuelven piezas defectuosas al proveedor y cómo lo registra hoy?
- G5. ¿Quién puede anular una venta del mismo día por error de captura? ¿Con clave del gerente?
- G6. ¿Qué tan seguido se equivocan los cajeros y necesitan anular?

### H. Cotizaciones y apartados
- H1. ¿Quién hace cotizaciones y en qué contexto: cliente en el mostrador, por teléfono o por WhatsApp?
- H2. ¿Las envía impresas, en PDF por WhatsApp o solo dice el precio de palabra?
- H3. ¿Qué tan común es apartar la pieza para el cliente? ¿Por cuántos días?
- H4. Cuando el cliente regresa a comprar lo cotizado, ¿cómo se encuentra la cotización: por número, por nombre del cliente o por teléfono?
- H5. Si el precio subió desde la cotización, ¿se respeta el precio cotizado o se cobra el nuevo? ¿Quién decide?
- H6. ¿El cliente suele pagar un anticipo al apartar?

### I. Compras y bodega
- I1. ¿Quién registra las compras: usted, el bodeguero o un encargado? ¿En la PC del mostrador o en otra?
- I2. ¿Registra la compra con la factura del proveedor en la mano, línea por línea? ¿Cuántas líneas trae una factura típica?
- I3. ¿Quiere que el sistema sugiera el último costo pagado a **ese** proveedor, a cualquier proveedor o el costo promedio?
- I4. ¿Actualiza precios de venta cuando cambia el costo de compra? ¿Quiere que el sistema se lo proponga al registrar la compra?
- I5. ¿Registrar compras puede interrumpir el uso del POS en la misma PC? ¿A qué hora del día se hace?

### J. Reportes y control
- J1. ¿Qué información revisa cada día, cada semana y cada mes?
- J2. ¿Revisa la utilidad por producto, por categoría o solo el total?
- J3. ¿Quiere que el cajero vea el total vendido en su turno o solo el gerente?
- J4. ¿Al cerrar caja, el cajero debe ver cuánto "debería haber" antes de contar (cierre abierto) o solo después (cierre ciego)? ¿El vendedor puede cerrar caja? Hoy no puede.
- J5. ¿Exporta reportes a Excel para su contador? ¿Cuáles?

### K. Catálogo e información visible
- K1. En la lista de productos y en la búsqueda del POS, ¿qué columnas son imprescindibles (código, nombre, número de parte, marca, precio, existencias, ubicación en bodega)?
- K2. ¿El cajero debe ver el costo o el margen? Hoy existe el permiso `com.costos.ver`.
- K3. ¿Tiene fotos de las piezas? ¿Le sirven en la búsqueda?
- K4. ¿Maneja ubicación física (estante, pasillo)? ¿Le serviría verla al vender?
- K5. ¿Qué tan importante es mostrar las piezas equivalentes o alternativas cuando la pedida no tiene existencias?

### L. Preferencias generales
- L1. ¿Prefiere que se vea más información a la vez (letra más pequeña, más columnas) o menos información más grande y clara?
- L2. ¿Minimizar clics para el cajero es prioritario aunque signifique aprender atajos?
- L3. ¿Le gustaría un sonido o señal visual fuerte cuando un escaneo falla (producto no encontrado)?
- L4. ¿Hay algo del sistema que usa hoy (o de uno anterior) que sus empleados extrañarían si no estuviera?
- L5. ¿Cuál es la queja más frecuente de sus empleados con la forma actual de trabajar (sistema o papel)?
- L6. ¿Puede dedicar una tarde a probar un prototipo del POS nuevo con un empleado real antes de que se aplique a todas las pantallas?
- L7. ¿Debe aparecer el logo del negocio en el POS o solo en los documentos impresos?

Total: 78 preguntas.

### Critical Files for Implementation
- `src/sistemashn/core/ui/app_shell.py`
- `src/sistemashn/core/ui/shell.py` (y `core/ui/router.py`, `core/modules/contracts.py` para el orden del menú)
- `src/sistemashn/comercial/ui/pos_view.py`
- `src/sistemashn/comercial/ui/cotizaciones_view.py` (y `compras_view.py` para unificar la captura de líneas)
- `src/sistemashn/core/ui/widgets.py` (y `comercial/ui/components.py` para los componentes compartidos)
