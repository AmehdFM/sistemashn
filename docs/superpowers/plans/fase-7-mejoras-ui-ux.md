# Fase 7 — Mejoras de UI/UX: plan ejecutable

Depende de: Fases 1-6 (todo el alcance funcional ya implementado). Fuente:
`docs/superpowers/plans/ui-ux-investigacion.md` (diagnóstico, referencias de otros sistemas y 38
decisiones ya respondidas por el dueño). **No toca la paleta Grafito y Vino ni el stack (Flet
1.0).**

## Principio rector: personalización acotada, no un sistema de temas

El dueño pidió explícitamente mantener personalización posible "sin volver un caos el soporte".
Como SistemasHN se vende a negocios distintos del mismo rubro con formas de trabajar distintas, la
mayoría de las 38 decisiones resultaron "configurable por negocio" en vez de un valor fijo. La
forma de resolver esto **no** es un editor de temas ni pantallas infinitamente configurables: es
una **lista corta y cerrada de interruptores de comportamiento**, todos con un valor por defecto
razonable, ninguno inventado por el usuario final (no hay "campos personalizados" ni "layouts a
medida"). Dos mecanismos, ambos ya existen en el proyecto y se reutilizan tal cual:

1. **Permisos por perfil/usuario** (`core.authorization`, ya implementado desde Fase 1): decide
   *quién* puede hacer una acción (cerrar caja, autorizar crédito, anular, aceptar devolución,
   crear cliente). No se inventa nada nuevo aquí salvo permisos puntuales que faltan — ver T7.1.
2. **`core_business`, ampliado con columnas nuevas** (mismo patrón que `fiscal_enabled`/
   `prices_include_isv`, ya existentes): decide *cómo se comporta* el sistema para ese negocio
   (exigir caja abierta, bloquear venta sin stock, política de impresión, etc.) — ver T7.2. Es una
   fila única por instalación, editable solo por quien tenga `core.ajustes.gestionar` (ya existe),
   en una pantalla nueva "Ajustes de operación" (T7.6). Nunca son más de una veintena de campos;
   si una decisión no cabe en un booleano/entero/enum corto, no se convierte en ajuste — se elige
   un comportamiento fijo razonable y se documenta como decisión de producto, no de negocio.

Esto mantiene el soporte manejable: cualquier instalación tiene exactamente el mismo código,
exactamente los mismos campos de ajuste, y una combinación de esos campos siempre produce un
comportamiento predecible y ya probado — no hay combinaciones no contempladas.

**Regla adicional, explícita del dueño**: cada ajuste tiene un valor por defecto que hace que el
sistema sea usable desde el primer arranque sin que el negocio configure nada — la personalización
es una posibilidad, no un requisito. El primer-arranque (`SetupService`, Fase 1) no pregunta nada
de esto; todos los campos de T7.2 nacen con su default (columna 3 de la tabla de T7.2) y quedan
disponibles para ajustar después en "Ajustes de operación" (T7.6) si el negocio lo necesita. Los
valores por defecto elegidos siguen el comportamiento ya implementado y probado en Fases 1-6
(p. ej. `cash_session_required=True` y `block_sale_without_stock=True` son exactamente cómo se
comportan hoy los servicios, así que una instalación nueva sin tocar Ajustes se ve idéntica al
sistema actual) — nunca un default "vacío" o "vago" que obligue a decidir antes de poder vender.

## Tareas

### T7.1 Permisos nuevos (`comercial/module.py`)

Solo dos huecos reales (el resto de "quién puede X" ya tiene permiso existente):
- `com.ventas.credito`: autorizar que una venta quede a crédito (distinto de `com.ventas.registrar`,
  que ya cubre confirmar cualquier venta al contado). `SaleService.confirm` lo exige además de
  `com.ventas.registrar` cuando `credit_amount > 0`.
- `com.ventas.descuento`: editar el precio de una línea por debajo del precio de catálogo (dentro
  del tope que fije `core_business.max_discount_percent`, ver T7.2). Sin este permiso, el campo de
  precio de línea en POS/cotizaciones queda de solo lectura.

Perfil `gerente` recibe ambos por herencia automática (`frozenset(p.code for p in _PERMISOS)`);
`vendedor` NO los recibe por defecto (el dueño de cada instalación se los otorga por usuario si
quiere, con el administrador de permisos ya existente de Fase 1 — no hace falta tocar UI de
permisos, ya lista filas por usuario).

Pruebas: `SaleService.confirm` rechaza crédito sin `com.ventas.credito`; rechaza precio de línea
distinto al de catálogo sin `com.ventas.descuento`, o lo acepta dentro del tope con el permiso.

### T7.2 `core_business`: columnas de operación nuevas

Ampliar el modelo (`core/settings/models.py::Business`) y su migración (`0005_operacion_ui.py`, ver
sección de migración) con:

- `cash_session_required: bool` (default `True`) — si `True`, `SaleService.confirm`/
  `AccountService.pay` con método efectivo exigen `cash_session_id` de una sesión abierta; si
  `False`, el efectivo se registra sin ligarlo a caja cuando no hay sesión (comportamiento actual).
- `block_sale_without_stock: bool` (default `True`) — si `True`, `SaleService.confirm` rechaza
  una línea sin disponibilidad suficiente (comportamiento actual, ya implementado); si `False`,
  permite continuar y deja el `on_hand` en negativo (requiere revisar el `CHECK` de `com_stock`:
  si se decide permitir negativo con este ajuste en `False`, el `CHECK on_hand >= 0` debe
  condicionarse — **decisión de implementación**: no se relaja el `CHECK` de base de datos; en su
  lugar, con el ajuste en `False`, el servicio permite vender hasta el disponible y el resto queda
  registrado como "pendiente de surtir" en un campo `SaleLine.backorder_qty` nuevo, sin tocar
  inventario por esa porción — evita romper el invariante de stock no negativo que protege toda la
  Fase 2).
- `print_receipt_policy: str` (`'auto'|'ask'|'never'`, default `'ask'`).
- `cashier_sees_own_sales_total: bool` (default `True`).
- `max_discount_percent: Rate` (default `0`, es decir sin descuento permitido aunque el usuario
  tenga `com.ventas.descuento` — el dueño debe subirlo explícitamente).
- `default_credit_days: int` (default `30`).
- `default_quote_validity_days: int` (default `8`).
- `pos_simplified_mode_enabled: bool` (default `True`) — activa el "modo mostrador" (T7.5) para
  perfiles sin acceso administrativo.
- `pos_exit_requires_manager_auth: bool` (default `False`) — si `True`, salir del modo mostrador a
  cualquier pantalla fuera de su lista reducida exige reautenticación con un usuario que tenga
  `core.usuarios.gestionar` (ya existe como permiso administrativo).
- `show_logo_in_app: bool` (default `True`) — ya hay soporte de logo (Fase 1); esto decide si se
  pinta en la barra lateral/encabezado además de en documentos.

`SettingsService`/`BusinessInput` (schemas) se amplían con estos campos, validados con Pydantic
(rangos: porcentajes 0–100, días > 0). `update_business` ya audita antes/después; no cambia su
forma, solo los campos que acepta.

Pruebas: cada campo nuevo tiene su default correcto en una base recién migrada; `update_business`
persiste y valida rangos; los servicios que a partir de T7.3-T7.5 leen estos campos lo hacen
correctamente en ambos valores.

### T7.3 Backend: comportamientos condicionados a `core_business`

- `SaleService.confirm`: lee `cash_session_required` y `block_sale_without_stock` de
  `core_business` (una lectura, misma transacción) y ajusta su validación como en T7.2. Exige
  `com.ventas.credito` cuando hay crédito y `com.ventas.descuento` + `max_discount_percent` cuando
  una línea trae `unit_price` menor al de catálogo.
- `AccountService.pay`: lee `cash_session_required` igual que ventas, para abonos en efectivo.
- `QuoteInput`/`SaleInput`: si no traen `credit_due_date`/`valid_until` explícitos, la UI (no el
  servicio) rellena con `clock().date() + default_credit_days/default_quote_validity_days` leídos
  de `core_business` — mantiene los servicios agnósticos de "valores por defecto de UI".
- `ReturnService.customer_return`/`supplier_return`: aceptan `sale_line_id`/`purchase_line_id`
  **opcionales** (antes obligatorios) — devolución "sin comprobante": si vienen `None`, exige en
  su lugar `product_id`, `qty`, `unit_price_override` (monto a acreditar, ya que no hay línea de la
  que tomar el precio) y dispara con `com.devoluciones.gestionar` igual que hoy, pero SIN tocar el
  acumulado de "no exceder lo vendido" (no hay línea contra la cual acumular). Auditoría marca
  `"sin_comprobante": true` en el detalle para que quede trazable en reportes.

Pruebas: cada rama nueva de cada servicio (bloquear/no bloquear stock, exigir/no exigir caja,
crédito sin permiso falla, descuento fuera de tope falla, descuento dentro de tope pasa,
devolución sin comprobante crea el registro con el monto indicado).

### T7.4 Catálogo: fotos de producto

- `com_product.image_path: str | None` (migración nueva). `save_product_image(data_dir, source) ->
  str` en `comercial/catalogo/service.py`, mismo patrón que `core/settings/service.py::save_logo`
  (valida tipo de imagen, tamaño máximo, copia a `data_dir/productos/<id>.<ext>`, reemplaza
  anterior).
- `CatalogService.set_image(actor, product_id, source: Path)` (`com.catalogo.gestionar`).
- UI: `widgets.image_picker` (ya existe, Fase 3) en el diálogo de producto de `catalog_view.py`;
  miniatura en la fila de resultados de búsqueda del POS (T7.5) y en la tabla de catálogo.

Pruebas: guardar/reemplazar imagen; producto sin imagen no falla en ningún listado; validación de
tipo/tamaño de archivo (reutiliza `sniff_image_extension`/`MAX_LOGO_BYTES` ya existentes en
`core/settings/service.py`, o su equivalente generalizado si conviene moverlos a un módulo común
de `core` — decidir al implementar y documentar).

### T7.5 POS: modo mostrador, ventas en espera y equivalencias sin stock

La pieza más grande de la fase, ya acotada por las decisiones del dueño:

- **Modo mostrador** (`pos_simplified_mode_enabled`): un `DesktopApp` (`core/ui/app_shell.py`)
  nuevo modo de render sin `shell.py` (sin barra lateral) para perfiles cuyo único permiso
  "fuerte" es de ventas (heurística simple: el perfil no tiene ningún permiso de grupo
  `Administración`/`Catálogo`/`Compras` — o más simple y explícito: un campo nuevo
  `simplified_by_default: bool` en `ProfileDef`, `True` para `vendedor`, `False` para
  `bodega`/`gerente`; el usuario puede tener overrides de permisos que igual respetan la lista
  reducida de pantallas del modo mostrador: POS, Caja, Cotizaciones, Buscar por vehículo,
  Devoluciones, Cuentas por cobrar). Un botón "Menú completo" visible siempre; si
  `pos_exit_requires_manager_auth` es `True`, pide usuario/contraseña de alguien con
  `core.usuarios.gestionar` antes de salir (diálogo simple, no una sesión aparte).
- **Ventas en espera (aparcar)**: `DesktopApp` mantiene una lista en memoria (no persistida en
  base de datos — se pierde si la app se cierra sin confirmar, aceptado explícitamente: nada se
  aparta de la integridad de datos porque nada aparcado toca inventario/caja hasta confirmarse) de
  "borradores de venta" (`estado` de `pos_view.py` serializado a un `dict` simple) por sesión de
  usuario. Botón "Aparcar venta" guarda el borrador actual y limpia el formulario; una lista
  "Ventas en espera (N)" permite retomar cualquiera, reemplazando el `estado` actual (si había una
  venta sin aparcar en curso, se pide confirmación antes de reemplazarla, mismo patrón que "venta
  sin confirmar" de P0.1 en la investigación).
- **Búsqueda de producto unificada**: el campo de código en POS, si no hay coincidencia exacta por
  código/barcode, abre un diálogo de resultados usando `CatalogSearchService` (ya combina
  proveedores de búsqueda registrados: nombre, código y, vía Repuestos, número de parte y
  equivalencia — sin dar prioridad a ninguno, como pidió el dueño), con foto (T7.4), precio y
  disponible por fila.
- **Equivalencias automáticas sin stock**: cuando una línea no tiene disponible suficiente (y
  `block_sale_without_stock` está activo, o incluso si no lo está, como aviso), el diálogo de
  búsqueda/agregar muestra debajo "Equivalentes disponibles" usando
  `PartService.equivalents(product_id)` ya existente (Fase 2), filtrados a los que sí tienen stock.
- **Confirmación con resumen** (D3): tras pulsar "Cobrar", un paso intermedio muestra el resumen
  (líneas, total, pagos, vuelto/crédito) con botones "Confirmar" / "Volver a editar" — reemplaza el
  cobro directo de un clic.
- **Pantalla de resultado**: tras confirmar, vuelto en tipografía grande, número de venta,
  crédito si aplica, y botones "Imprimir" (si `print_receipt_policy != 'never'`; si es `'auto'` se
  imprime sin preguntar y este paso se salta) y "Nueva venta".
- Logo en la barra lateral/modo mostrador condicionado a `show_logo_in_app` (ya se pinta hoy sin
  condición; solo se envuelve en el `if`).

Pruebas de UI (construcción sin lanzar, con las combinaciones de ajustes en `True`/`False`);
pruebas de servicio para aparcar/retomar si se decide mover ese estado a un objeto testeable en
vez de vivir solo dentro de closures de `pos_view.py` (recomendado: extraer un pequeño
`ParkedSalesStore` en `comercial/ui/` con pruebas unitarias propias, ya que es lógica no trivial).

### T7.6 Pantalla "Ajustes de operación" y "Configuración avanzada"

- Nueva sección en `core/ui/views/business_view.py` (o una pantalla hermana
  `operation_settings_view.py`, decidir al implementar según qué tan grande quede el formulario)
  con los campos de T7.2, agrupados y con texto de ayuda breve por campo (no jerga técnica).
- `ScreenDef` gana un campo `advanced: bool = False`. Pantallas marcadas `advanced=True`
  (`Importar catálogo`, `Licencia`, y las que se decida al revisar la lista completa del menú) se
  agrupan en una sub-sección plegada "Configuración avanzada" al final de la barra lateral en vez
  de mezclarse con el uso diario — no se ocultan del todo (nadie pierde acceso), solo bajan de
  prioridad visual.
- `ProfileDef` gana un campo opcional `home_route: str | None`; si está definido, `app_shell.py`
  lo usa como ruta inicial para ese perfil en vez de la primera visible.

Pruebas: `advanced=True` no aparece en el grupo principal del menú pero sí en "Configuración
avanzada"; `home_route` decide la pantalla inicial cuando está definido; sin definir, se mantiene
el comportamiento actual (primera visible).

## Migración

`0005_operacion_ui.py`: columnas nuevas en `core_business` (T7.2), `com_product.image_path`
(T7.4), `com_sale_line.backorder_qty` (T7.3, nullable, default 0), y hace `sale_line_id`/
`purchase_line_id` nullable en `com_customer_return`/`com_supplier_return` (T7.3, requiere
`batch_alter_table` igual que el CHECK de `com_account` en `0004`). Verificada contra
`tests/core/db/test_schema_matches_models.py`.

## Fuera de alcance de esta fase (documentado, no implementado)

- Prueba técnica real en Windows de `DatePicker`/`on_keyboard_event`/`SnackBar`/foco (queda como
  paso previo obligatorio a T7.5 antes de dar por buena la elección de `DatePicker`; si falla en
  la máquina real, T7.5 cae a los campos de texto ya existentes sin bloquear el resto del plan).
- Cambio de cajero con PIN corto (A7): el dueño no lo priorizó; no se implementa en esta fase.
- Soporte de otra moneda (D15): descartado explícitamente.
- Pantalla táctil (B4): descartado explícitamente, no se diseñan controles táctiles especiales.
- Ubicación física en bodega (K4): descartado.
- Actualizar precio de venta automáticamente al cambiar costo de compra (I4): descartado, son
  pantallas separadas.

## Salida de fase

Suite verde; migración `0005_operacion_ui` sobre base con datos de Fases 1-6; recorrido manual:
crear una instalación con ajustes por defecto y otra con `cash_session_required=False` y
`block_sale_without_stock=False`, confirmar que ambas se comportan distinto y de forma predecible;
probar el modo mostrador entrando como vendedor (menú reducido) y como gerente (menú completo);
aparcar dos ventas en el POS, retomarlas, confirmar ambas; vender un producto sin stock y ver
aparecer sus equivalentes; agregar foto a un producto y verla en la búsqueda del POS; devolver una
pieza sin comprobante original. Commit `feat: fase 7 mejoras ui-ux`.
