# Matriz de migración de pantallas

Esta matriz controla el programa:

- **Pendiente:** no inició.
- **En curso:** cambio incompleto.
- **Migrada:** usa patrón objetivo y compila.
- **Conforme:** pasó QA visual, teclado, estados y DPI con evidencia.

Los cambios existentes al 20 de septiembre de 2026 son línea base, pero no se marcan automáticamente como conformes.

| Superficie | Arquetipo | Estado inicial | Tarea | Prioridad | Criterio específico |
|---|---|---|---:|---|---|
| `FormDashboardBase` | Shell | Parcialmente migrada | 5 | Crítica | Grupos, scroll interno, pie fijo, 220/56, foco y disposición sin fugas. |
| `SidebarItem` | Navegación | Parcialmente migrada | 5 | Crítica | Activo no depende solo de color; tooltip y accesibilidad colapsado. |
| `ModuleLauncherControl` | Inicio transitorio | Parcialmente migrada | 5 | Alta | Orden por frecuencia, tokens y sin fuentes locales. |
| `FormArranque` | Asistente | Parcialmente migrada | 8 | Alta | Contenedor estable a 100/125/150 % sin cortes. |
| `ActivacionStepControl` | Asistente | Parcialmente migrada | 8 | Alta | Progreso, error local, foco y acción única. |
| `PrimerUsuarioStepControl` | Asistente | Parcialmente migrada | 8 | Alta | Tab lógico, validación y contraseña accesible. |
| `DatosNegocioStepControl` | Asistente | Parcialmente migrada | 8 | Alta | Campos largos, logo y acción sin desplazamientos. |
| `LoginStepControl` | Acceso | Parcialmente migrada | 8 | Crítica | Enter inicia una vez, error genérico, foco predecible. |
| `AjustesControl` | Configuración | Parcial | 8 | Alta | Secciones de negocio, identidad, CAI, catálogos y usuarios. |
| `FacturacionCaiControl` | Configuración | Parcial | 8 | Alta | Rango/vigencia comprensibles y advertencias correctas. |
| `FormUnidadesMedida` | Catálogo | Parcial | 6 | Media | Alta + tabla, edición clara, cantidades y teclado. |
| `FormRegistro` | Formulario | Parcial | 7 | Alta | Validación, rol, Guardar/Cancelar y estado ocupado. |
| `InventarioControl` | Maestro-detalle | En rediseño local | 9 | Crítica | Filtros, tarjetas responsivas, selección, paginación y retorno. |
| `ProductCard` | Elemento de lista | En rediseño local | 9 | Alta | Jerarquía estable, inactivo y stock con señal no cromática. |
| `ProductDetailControl` | Detalle/edición | En rediseño local | 9 | Crítica | Modos únicos, secciones, ayudas y una primaria. |
| `FormCategoriaRapida` | Diálogo pequeño | Parcial | 7 | Media | Alta por teclado, error local y retorno de selección. |
| `FormArmarPaquete` | Transacción breve | Parcial | 11 | Alta | Búsqueda, componentes, cantidad y Guardar separados. |
| `FormImportarExcel` | Importación | Parcial | 11 | Alta | Plantilla→archivo→resumen; estados accesibles. |
| `TercerosControl` clientes | Lista | Parcial | 6 | Alta | Patrón referencia, Enter/doble clic, búsqueda y estados. |
| `TercerosControl` proveedores | Lista | Parcial | 6 | Alta | Mismo layout que clientes con textos correctos. |
| `TerceroCamposControl` | Formulario reusable | Parcial | 7 | Alta | Anchos semánticos, roles y errores junto a campos. |
| `FormTercero` | Diálogo | Parcial | 7 | Alta | Alta rápida sin duplicar layout ni validación. |
| `FormPerfilTercero` | Detalle/edición | Parcial | 7 | Alta | Datos, cuentas relacionadas y primaria coherente. |
| `ComprasControl` | Lista | Parcial | 6 | Alta | Toolbar ordenada, filtros, estados y paginación. |
| `FormRegistrarCompra` | Transacción | Parcialmente migrada | 11 | Crítica | Proveedor, líneas, crédito, total y registro visibles. |
| `FormImportarComprasExcel` | Importación | Parcial | 11 | Alta | Misma secuencia que importación de inventario. |
| `PosControl` | Transacción | Parcialmente migrada | 10 | Crítica | Venta sin mouse, total/Cobrar visibles y caja clara. |
| `FormCobroEfectivo` | Diálogo transaccional | Parcial | 10 | Crítica | Recibido/vuelto, Enter único y error de insuficiencia. |
| `VentasControl` | Lista | Parcial | 6 | Alta | Exportar/Anular secundarios, selección y paginación. |
| `CajaControl` | Estado/lista | Parcial | 6 | Crítica | Una primaria según caja abierta/cerrada. |
| `FormAbrirCaja` | Diálogo pequeño | Parcial | 7 | Crítica | Importe, foco, confirmación única y DPI. |
| `FormCerrarCaja` | Diálogo pequeño | Parcial | 7 | Crítica | Resumen, contado y diferencia legible. |
| `CuentasPorCobrarPanel` | Lista | Parcial | 6 | Alta | Saldo/estado, pago condicionado y estados. |
| `CuentasPorPagarPanel` | Lista | Parcial | 6 | Alta | Misma anatomía/formato que CxC. |
| `FormRegistrarPago` | Diálogo pequeño | Parcial | 7 | Crítica | Límite de saldo, método, error y doble envío impedido. |

## Evidencia para marcar Conforme

```text
Pantalla:
Commit:
Resoluciones/DPI:
Recorrido de teclado:
Estados probados:
Camino de error:
Resultado:
Captura o nota:
```

No reutilizar una evidencia para pantallas distintas, salvo el mismo control reusable probado explícitamente en ambos modos.

## Seguimiento del programa

| Tarea | Estado | Evidencia | Pendiente |
|---|---|---|---|
| 1. Línea base y reglas estáticas | Completada | `validar-ui.ps1` operativo; 14 hallazgos reales registrados como deuda de tokens y consumidores. Compilación del ejecutable correcta. | Ninguno. |
| 2. Tokens, métricas y botones | Completada | Validador UI sin hallazgos; variantes, estado ocupado, métricas y anchos semánticos disponibles. Compilación correcta. | Validación visual manual pendiente de las pantallas consumidoras. |
| 3. Componentes estructurales | Migrada | Ayuda contextual, encabezados, banner, toolbar, filtros y extensiones de formulario creados; build y validador correctos. | QA visual 100/125/150 % pendiente por falta de sesión de aplicación. |
| 4. Tablas, estados y paginación | Migrada | Contratos de columnas en `GridStyler`, estados explícitos y resumen de rango en paginación implementados; build y validador correctos. | QA manual de estados, navegación por teclado y DPI pendiente. |
| 5. Navegación y shell | Migrada | Metadatos de grupo/orden en módulos, registro agrupado y sidebar con medidas centralizadas implementados; build y validador correctos. | QA manual de navegación, foco, modo colapsado y resoluciones/DPI pendiente. |
| 6. Listas y mantenimiento | Migrada | Terceros, cuentas, compras, ventas, caja y unidades usan toolbar, filtros o anchos semánticos compartidos; build y validador correctos. | QA manual de teclado, estados, resolución y DPI pendiente para cada pantalla. |
| 7. Diálogos y formularios breves | Migrada | Pie Guardar/Cancelar compartido, foco inicial, Enter/Escape y anchos monetarios en caja, pago, categoría, tercero, cobro y registro; build y validador correctos. | QA manual de doble Enter, textos largos, resolución y DPI pendiente. |
| 8. Arranque y ajustes | Migrada | Arranque con foco y envío por teclado; Ajustes separados en Negocio, Identidad, Facturación, Catálogos y Usuarios, conservando una única acción general de guardado; build y validador correctos. | QA manual de los recorridos de base nueva/configurada, resolución y DPI pendiente. |
| 9. Inventario maestro-detalle | Migrada | Lista con encabezado, tarjetas accesibles y detalle con flujo Volver, ayudas contextuales y modos existentes centralizados; build y validador correctos. | QA manual de búsqueda, edición, cancelación, guardado, tamaños de tarjeta, DPI y handlers repetidos pendiente. |
| 10. POS y cobro | Migrada | Ctrl+F, Enter, Delete protegido, F12, botón de cliente accesible y foco restaurado; cobro conserva total, recibido, vuelto y envío único; build y validador correctos. | QA manual de caja, contado/crédito/ISV, stock, cliente nuevo, teclado y DPI pendiente. |
| 11. Compras, paquetes e importaciones | Migrada | Compra con jerarquía de acciones y campos semánticos; importaciones con selección y confirmación explícita, ruta con tooltip y resumen; build y validador correctos. | QA manual de archivos ausentes, inválidos, mixtos y válidos; paquete vacío/duplicado/cantidad inválida y DPI pendiente. |
| 12. Accesibilidad y DPI | En curso | `FormBase` usa `AutoScaleMode.Dpi`; `ApplicationConfiguration.Initialize()` se conserva como configuración WinForms soportada; accesibilidad y atajos estáticos auditados. | Ejecutar aplicación en 1366×768 y 1920×1080 a 100/125/150 %, entre monitores si aplica, y completar checklist visual/teclado. |
