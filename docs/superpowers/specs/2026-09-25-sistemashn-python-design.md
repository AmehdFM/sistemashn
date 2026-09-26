# SistemasHN: diseño de la nueva implementación

Fecha: 2026-09-25
Estado: diseño conversado y aprobado; pendiente de revisión de este documento
Destino: `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`

## 1. Propósito y alcance

SistemasHN es una familia de aplicaciones de escritorio para negocios pequeños de Honduras. Cada cliente instala el producto de su rubro en una PC Windows y tiene una base de datos local propia. El funcionamiento diario, la licencia y la recuperación básica no dependen de internet. Se vende con licencia perpetua por computadora. La primera vertical es autorepuestos; después se prevén ferretería y clínica. Cada rubro tiene un instalador común para todos sus clientes, personalizado en el primer arranque con licencia, nombre y logo.

Esta implementación empieza desde cero en el repositorio `AmehdFM/sistemashn`. El código y la base de SQL Server/C# anteriores no se migran ni se reutilizan. Su funcionalidad y documentación son referencias históricas, no contratos de compatibilidad. La meta incluye todo el alcance funcional alcanzado anteriormente, más las decisiones de esta especificación. No se entrega a un cliente antes de contar con instalación, respaldo/restauración y comprobación del flujo completo.

Una instalación usa una PC, un monitor y una instancia de la aplicación. No hay puestos independientes simultáneos, red local, sincronización entre sucursales, servidor de negocio ni contabilidad general. Puede haber varios empleados con cuentas distintas, usando la PC por turnos. El equipo de referencia para comprobar rendimiento es Windows con 4 GB de RAM, CPU básica y disco duro mecánico. Carga típica: unos 1,000 productos y varias decenas de ventas diarias; la prueba de carga incluirá jornadas cercanas a cien ventas.

## 2. Stack y límites de componentes

Stack elegido: Python 3.14.x, Flet, SQLAlchemy 2.x, SQLite, Alembic, Pydantic, openpyxl, argon2-cffi, cryptography y pytest. Se incorporará una biblioteca de PDF y las herramientas necesarias para empaquetar e imprimir tras una prueba técnica de Windows. Se fijarán versiones exactas verificadas en el plan de implementación, no en esta especificación.

El repositorio contiene cuatro límites lógicos:

| Componente | Responsabilidad | Dependencias permitidas |
|---|---|---|
| Core | Arranque, configuración, identidad, permisos, auditoría, licencia, recuperación, respaldos, actualizaciones, tema y navegación común | Ninguna vertical |
| Comercial | Productos, unidades, inventario, proveedores/clientes como participantes comerciales, compras, cotizaciones, ventas, caja, pagos, crédito, devoluciones, documentos y reportes comunes | Core y contratos internos |
| Repuestos | Número de parte, equivalencias, compatibilidad vehicular, kits y pantallas/reglas propias | Core y Comercial |
| Aplicación Repuestos | Composición, registro de módulos y perfiles, arranque y empaquetado | Los tres anteriores |

Core no conoce Repuestos ni Clínica. Comercial no contiene códigos OEM ni vehículos. Una vertical registra pantallas, permisos y perfiles sugeridos mediante contratos explícitos; la aplicación compone las implementaciones al empaquetarse. No se exige carga dinámica de plugins. Ferretería podrá reutilizar Core y Comercial; clínica reutilizará Core y solo las capacidades comerciales pertinentes. Ninguna vertical futura se implementa en este primer programa.

La interfaz Flet llama a servicios de aplicación. Los servicios comprueban permisos, ejecutan reglas y coordinan repositorios SQLAlchemy dentro de una transacción. Pydantic valida entradas y contratos en límites de la aplicación, sin sustituir las restricciones de la base. Las reglas de negocio no viven en controles visuales. Las tablas pertenecen al componente que define sus invariantes y se almacenan en un solo archivo SQLite por instalación.

## 3. Datos, concurrencia e invariantes

Cada operación que cambia dinero, existencias o documentos es atómica. Una venta guarda encabezado, líneas, costo histórico, pagos, caja, movimientos de inventario y auditoría en una sola transacción. Si falla cualquier paso, no se confirma ninguna parte. Las compras, devoluciones, abonos, apartados y ajustes siguen el mismo principio. Los servicios comprueban existencias y permisos dentro del flujo transaccional; el stock vendible nunca se vuelve negativo. Una factura emitida no se elimina ni reutiliza su numeración.

Los cálculos monetarios usan `Decimal`; el esquema define una representación exacta para dinero y costo promedio, con reglas explícitas de redondeo y tasas. Se evita depender de `float` de SQLite para importes. Las ventas guardan precio, tasa, costo y composición de kit del momento. El costo del inventario se calcula por promedio ponderado y cada venta conserva una fotografía de su costo para reportes históricos.

El inventario es simple y no modela estanterías ni ubicaciones. Distingue unidades disponibles, apartadas y no vendibles. Un movimiento inmutable explica cada entrada, salida o cambio de estado. Los ajustes manuales requieren permiso, motivo y auditoría. Las piezas defectuosas devueltas quedan fuera del stock vendible hasta su resolución o devolución al proveedor.

La aplicación será de una sola instancia de trabajo por negocio, pero habrá tareas en segundo plano para importación, generación de PDF/reportes y preparación de respaldos. Una sesión SQLAlchemy pertenece a una sola tarea o hilo y nunca se comparte. Las transacciones de escritura serán cortas, con política explícita de espera/reintento ante `database is locked`; no se bloqueará el hilo visual con tareas largas. Se habilitarán claves foráneas y se escogerán y probarán los ajustes de durabilidad de SQLite en el prototipo. Los respaldos usarán un mecanismo consistente de SQLite, no una copia ingenua del archivo abierto.

Alembic versiona el esquema. Las migraciones de SQLite que necesitan recrear tablas preservan datos e índices y se prueban sobre copias de bases con datos reales de prueba. Una actualización comprueba versión de esquema y crea/verifica un respaldo antes de migrar.

## 4. Flujos comerciales

### Catálogo y compras

El catálogo tiene productos, códigos, categorías, unidades y cantidades fraccionarias cuando la unidad lo permite. Se puede importar y exportar Excel con plantilla y validación por fila. Los proveedores y clientes pueden ser la misma persona o negocio. Compras al contado o crédito incrementan existencias y alimentan el costo promedio. Se conservan precios históricos por proveedor para compararlos. La compra a crédito crea una cuenta por pagar; los pagos parciales actualizan su saldo sin borrar el historial.

Repuestos añade números de parte y equivalentes, original/genérico y compatibilidad por marca, modelo y rango de años. Un kit es un producto comercial sin stock propio: la venta descuenta sus componentes. La composición y costos aplicados se guardan históricamente en la venta.

### Cotizaciones y apartados

Una cotización se guarda con cliente opcional, líneas, precios y vigencia. Puede apartar inventario por decisión del empleado; el apartado tiene vencimiento y reduce disponibilidad sin cambiar el stock físico. Al vencer o cancelar, libera unidades. La liberación se comprueba al iniciar operaciones relevantes y al consultar disponibilidad; no depende de que la PC esté encendida a la hora exacta del vencimiento.

Al convertirla en venta, se comprueban existencias y se muestran cambios de precio o disponibilidad al empleado. El precio cotizado se respeta si decide continuar y hay stock; si no hay unidades suficientes, la conversión no confirma una venta imposible. La operación conserva el vínculo con la cotización y libera o consume el apartado en la misma transacción.

### Ventas, pagos y caja

El POS permite búsqueda por código, nombre, parte y equivalencia; un lector USB que actúe como teclado es opcional. Las ventas tienen siempre identidad y numeración interna. El CAI y demás datos de factura legal son información adicional cuando corresponde. Existen facturas genéricas y legales con formato base común y campos legales adicionales. Las reglas y formatos fiscales específicos se contrastarán con fuentes hondureñas vigentes antes de habilitar una factura legal para clientes.

Se aceptan efectivo, transferencia y tarjeta, solos o combinados en una misma venta o abono. El efectivo recibido y vuelto se calculan contra el total confirmado. Las sesiones de caja registran apertura, movimientos y cierre; el historial de ventas y anulaciones es distinto de la pantalla de cobro. Ventas a crédito crean cuenta por cobrar con vencimiento; los abonos parciales nunca exceden el saldo. Compras a crédito y cuentas por pagar siguen el mismo modelo de historial y saldos.

Se permiten anulaciones y devoluciones parciales, conservando documento y auditoría. Una devolución puede dar lugar a reembolso, cambio de pieza o saldo a favor. La pieza devuelta se clasifica como vendible o no vendible. Si se devuelve al proveedor, se registra si éste entrega reemplazo, reembolso o crédito para una compra futura. El diseño detallado de esta área definirá las restricciones de facturas legales y pagos previos antes de implementarla.

### Documentos y reportes

Cotizaciones, comprobantes de compra y facturas se imprimen en formato térmico o carta y pueden guardarse como PDF. Nombre y logo del negocio aparecen donde corresponda. Hay exportación Excel de listados y reportes. La reportería básica incluye ventas y utilidad estimada por período, existencias bajas, saldos por cobrar/pagar y cierres de caja. Las consultas se paginan; no se carga el catálogo completo para mostrar una pantalla.

## 5. Identidad, permisos y auditoría

El Core define el catálogo de permisos comunes y perfiles sugeridos; cada vertical aporta permisos y perfiles propios. Al crear un empleado, el administrador selecciona un perfil y puede ajustar los permisos individuales. El administrador tiene acceso completo. El menú y los controles ocultan funciones sin permiso, y cada servicio verifica el permiso otra vez antes de actuar. Cambios de permisos, operaciones económicas, ajustes y recuperaciones quedan auditados con usuario, fecha, acción y referencia.

Las contraseñas se almacenan con Argon2. El primer arranque configura el negocio y crea administrador. Para recuperar esa cuenta se entregan códigos de un solo uso durante la instalación. Una vía de soporte usa un desafío de la instalación y una autorización firmada por el vendedor; no hay contraseña maestra permanente ni un secreto universal dentro de la app. La recuperación se registra en auditoría.

La licencia perpetua se emite con firma asimétrica y se verifica offline contra la máquina. La herramienta que firma claves y las claves privadas no se distribuyen. Los cambios de hardware requieren un procedimiento de reactivación documentado. La licencia del programa no depende de que funcione el servidor de actualizaciones.

## 6. Apariencia, instalación y operación

Se conserva la paleta Grafito y Vino: principal `#8B2635`, principal oscuro `#6E1E2A`, barra lateral `#27272A`, fondo de contenido `#FAFAF9`, además de los estados visuales del `UiTheme` histórico. El diseño nuevo respeta contraste, estados vacíos y de error, teclado y escalado de Windows. Nombre y logo del negocio son configurables; Elements System permanece como marca del proveedor donde corresponda.

Cada vertical produce su instalador Windows. Código instalado y datos del cliente quedan separados. El instalador no exige una conexión a internet para iniciar el producto una vez entregado el paquete y la licencia. El respaldo operativo es manual, con recordatorios y fecha/estado visible del último respaldo. Por defecto puede guardarse en el mismo disco y se recomienda una USB o disco externo. La restauración se prueba sobre una instalación de ensayo antes de ofrecer el producto.

Las actualizaciones normales se notifican; el administrador decide cuándo instalarlas. Se descargan por internet cuando hay conexión o se importan como paquete local (por ejemplo ZIP). El paquete contiene manifiesto, versión, hashes y firma verificable. Un actualizador separado prepara el reemplazo del programa, respalda la base, migra y verifica arranque; si falla, recupera binario y base coherentes. Un servicio remoto autenticado puede marcar y ordenar una actualización obligatoria sin autorización del administrador local: el cliente conectado la descarga e instala automáticamente después de terminar la operación activa. Un equipo desconectado no puede recibir la orden hasta reconectarse. No se interrumpe una transacción de venta, pago, migración o respaldo. El mecanismo de comunicación y autenticación de órdenes se detallará y probará antes de habilitar control remoto.

## 7. Verificación y entregas

Primero se ejecuta una prueba técnica pequeña en Windows con Python 3.14, Flet empaquetado, SQLite, SQLAlchemy, una migración Alembic y una actualización recuperable; se mide inicio, memoria y respuesta en el equipo de referencia. La prueba responde si el stack cumple las restricciones antes de construir el producto completo.

El plan general desglosará dependencias y orden: base técnica; Core y seguridad; catálogo/inventario; compras; cotizaciones/apartados; POS/caja/ventas; crédito; devoluciones; documentos/reportes; instalación, licencias, respaldo, actualización y aceptación integral. Los planes específicos por área describirán modelo de datos, permisos, pantallas, casos de uso, invariantes, errores, pruebas pytest, pruebas manuales y criterios de terminado. El alcance grande se implementará por incrementos integrables, sin esperar al final para probar flujos de dinero.

Las pruebas críticas cubrirán redondeo y costo promedio; compra/venta/kits; apartado y vencimiento; saldo y abonos; anulación y devolución; pérdida de energía simulada y recuperación; migraciones sobre datos existentes; respaldo/restauración; permisos en UI y servicio; firma de licencias y actualizaciones. No se afirmará conformidad fiscal o rendimiento en el hardware objetivo sin verificación de esas condiciones.

## 8. Decisiones diferidas a los planes específicos

El diseño aprobado fija comportamiento, no inventa detalles fiscales ni un proveedor de actualizaciones. Cada plan específico resolverá y registrará antes de implementar: reglas vigentes del SAR y formato de factura; esquema exacto y redondeo de importes/cantidades; biblioteca de PDF e impresión; estrategia concreta de empaquetado; endpoints, claves y operación del canal remoto; frecuencia y UX de recordatorios; compatibilidad de periféricos; y las restricciones legales/técnicas de devoluciones de factura con CAI. Estas son verificaciones y decisiones de implementación, no permiso para omitir capacidades aprobadas.
