# SistemasHN: plan general de desarrollo

> **Para agentes de implementación:** leer primero la [especificación](../specs/2026-09-25-sistemashn-python-design.md) y el plan del área. Ejecutar tareas pequeñas con prueba, verificación y commit. No asumir que la documentación equivale a funcionalidad implementada.

**Objetivo:** entregar desde cero un instalador Windows de Repuestos que cubra las funciones acordadas, funcione sin conexión durante la operación comercial y mantenga Core y Comercial reutilizables.

**Arquitectura:** UI Flet → servicios de aplicación → repositorios SQLAlchemy y transacciones SQLite. Core no depende de verticales; Comercial depende de Core; Repuestos compone ambos y agrega datos y flujos de autopartes.

**Stack:** Python 3.14.x, Flet, SQLAlchemy 2.x, SQLite, Alembic, Pydantic, openpyxl, argon2-cffi, cryptography, pytest. PDF, impresión y empaquetado se eligen en el prototipo.

**Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`

## Restricciones globales

- Una PC con Windows 10 o superior, un monitor y una instancia; empleados distintos usan la máquina por turnos.
- Equipo objetivo de 4 GB de RAM, CPU básica y HDD; ~1,000 productos y varias decenas de ventas por día, con ensayo cercano a cien.
- Dinero en `Decimal` y representación exacta persistida; escrituras de negocio atómicas y numeración de factura no reutilizable.
- Una sesión SQLAlchemy por tarea/hilo, escrituras cortas, claves foráneas activas y respaldo consistente de SQLite.
- Offline para venta, licencia y restauración local; internet solo para servicios opcionales y recepción de actualizaciones.
- No implementar ferretería o clínica en el primer instalador. No migrar datos ni código del sistema anterior.

## Secuencia y puertas de salida

| Etapa | Entrega verificable | Depende de | Plan |
|---|---|---|---|
| 0 | Prototipo en Windows 10 o superior: Flet empaquetado, SQLite/Alembic, respaldo, recuperación por paquete y medidas en la PC del propietario | Ninguna | [Base y Core](2026-09-25-base-core.md) |
| 1 | Arranque, configuración, identidad, licencia offline, permisos en UI/servicio y auditoría | 0 | [Base y Core](2026-09-25-base-core.md) |
| 2 | Catálogo, importación Excel, inventario, costo promedio, kits y compatibilidad de repuestos | 1 | [Catálogo e inventario](2026-09-25-catalogo-inventario.md) |
| 3 | Compras, proveedores, cuentas por pagar y abonos parciales | 2 | [Compras y crédito](2026-09-25-compras-credito.md) |
| 4 | Cotizaciones con apartado opcional, ventas, facturación genérica, pagos mixtos, caja y cuentas por cobrar | 2 y 3 | [Cotizaciones, POS y caja](2026-09-25-cotizaciones-pos-caja.md) |
| 5 | Anulaciones, devoluciones parciales, proveedor, PDF/impresión y reportes básicos | 4 | [Devoluciones y documentos](2026-09-25-devoluciones-documentos.md) |
| 6 | Instalador, respaldo/restauración, actualizador firmado normal/obligatorio y aceptación integral | 1–5 | [Operación y entrega](2026-09-25-operacion-entrega.md) |

La etapa 0 es una decisión de viabilidad. Registrar medidas y condiciones en la PC del propietario; él acepta o rechaza el rendimiento observado y luego puede contrastarlo en otras máquinas. Si Python 3.14, Flet o el empaquetado no cumplen, revisar el diseño antes de escalar. El prototipo no autoriza reducir funciones sin acuerdo.

## Orden dentro de cada etapa

1. Fijar interfaces y migración de la etapa; documentar decisiones aún abiertas del área.
2. Crear pruebas de reglas y de transacciones fallidas; ejecutar para comprobar que fallan por la capacidad faltante.
3. Implementar servicios y repositorios; verificar las pruebas y migración sobre una base con datos anteriores.
4. Añadir UI que consume servicios y oculta operaciones no autorizadas; comprobar manualmente teclado, errores y estados vacíos.
5. Ejecutar integración de la etapa, medir las rutas críticas y registrar un commit pequeño por capacidad terminada.

## Recorrido de aceptación integral

Instalar sin internet; activar con licencia offline; crear negocio y administrador; crear empleado restringido; importar productos y asociar piezas; registrar compra a crédito y abono; cotizar y apartar con vencimiento; vender kit y pieza con pagos mixtos y costo conservado; emitir comprobante genérico y factura legal validada; abonar venta a crédito; devolver parcialmente una pieza defectuosa con saldo a favor; cerrar caja; exportar reportes; respaldar, restaurar en ensayo y actualizar desde internet y desde paquete local. Comprobar que un rol restringido no ve ni puede invocar servicios prohibidos. Simular interrupción en venta, migración y actualización sin dejar estados parciales.

## Riesgos que gobiernan el orden

- Flet/impresoras/instalador en Windows 4 GB/HDD: se miden antes de construir pantallas masivas.
- SQLite y dinero exacto: esquema, bloqueos, costo y recuperación se fijan antes del POS.
- Factura legal hondureña: revisar requisitos vigentes y escenarios de anulación/devolución antes de habilitarla.
- Orden remota obligatoria: autenticar, firmar, esperar fin de operación y ensayar reversión antes de activarla.
- Backups en mismo disco: mostrar recomendación externa y probar restauración; existencia del archivo no prueba recuperabilidad.

## Criterio de finalización del producto inicial

No basta una demostración visual. Se exige instalador reproducible, migración segura, pruebas de reglas y servicios, pruebas manuales de Windows/impresoras, restauración ensayada, escenarios de error y flujo integral anterior con datos representativos. Documentar limitaciones verificadas, sin afirmar cumplimiento fiscal o rendimiento no medido.
