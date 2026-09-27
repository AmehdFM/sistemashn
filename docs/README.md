# Documentación de SistemasHN Python

Esta rama inicia la implementación nueva desde cero. El sistema C#/SQL Server anterior se usa como referencia funcional e histórica; no se migra su código ni su base de datos.

## Orden de lectura

1. [Diseño del producto](superpowers/specs/2026-09-25-sistemashn-python-design.md): alcance, decisiones acordadas e invariantes.
2. [Plan general](superpowers/plans/2026-09-25-plan-general.md): secuencia de entregas, dependencias y criterios de salida.
3. [Etapa 0: viabilidad Windows](superpowers/plans/2026-09-26-etapa-0-viabilidad-windows.md): tareas ejecutables, pruebas y validación en la máquina objetivo.
4. Planes específicos: [base y Core](superpowers/plans/2026-09-25-base-core.md), [catálogo e inventario](superpowers/plans/2026-09-25-catalogo-inventario.md), [compras, crédito y proveedores](superpowers/plans/2026-09-25-compras-credito.md), [cotizaciones, POS y caja](superpowers/plans/2026-09-25-cotizaciones-pos-caja.md), [devoluciones y documentos](superpowers/plans/2026-09-25-devoluciones-documentos.md), [operación, entrega y actualizaciones](superpowers/plans/2026-09-25-operacion-entrega.md).

## Convenciones de ejecución

- Los planes son una ruta de desarrollo, no afirmaciones de que el software exista ya. Cada tarea se completa con pruebas y revisión antes de avanzar.
- Los detalles fiscales de Honduras se verifican con normativa vigente antes de emitir facturas legales reales. La documentación evita declarar conformidad fiscal sin esa comprobación.
- Las versiones exactas de dependencias y las herramientas de PDF, impresión y empaquetado se fijan tras el prototipo Windows. Un fallo de viabilidad reabre el diseño antes de ampliar el código.
- Cada módulo tiene servicios con permisos y transacciones; la UI oculta acciones no autorizadas y no es la única barrera.
- La primera entrega instalable es Repuestos. Ferretería y Clínica son extensiones futuras y no bloquean esa entrega.

## Estado

Etapa 0 (viabilidad Windows) y Fase 1 (Core: módulos, autorización, identidad, auditoría,
licencia, ajustes/primer arranque, UI base y pantallas Core) están terminadas. La Fase 2
(catálogo, inventario y Repuestos) está prácticamente cerrada: catálogo, libro de inventario,
kits, partes/equivalencias/vehículos e importación de Excel están hechos; las pantallas (T2.6)
están en curso, falta registrar la vista de unidades/categorías y la pantalla de kits. La Fase 3
(compras y crédito) está en curso: contrapartes/numeración/pagos hechos, compras y pantallas
pendientes, cuentas por pagar/cobrar en curso. Las Fases 4 a 6 (cotizaciones/POS/caja,
devoluciones/documentos, operación/entrega) todavía no comienzan. Ver
`docs/validation/progreso.md` para el detalle tarea por tarea.
