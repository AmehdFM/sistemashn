# Catálogo, inventario y Repuestos: plan de área

**Meta:** consultar y mantener unos 1,000 productos con existencias y costo confiables, incluyendo equivalencias, compatibilidad y kits. **Depende de:** Base y Core. **Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.

## Propiedad de datos

`comercial` posee producto, unidad, categoría, precio, movimiento, saldo disponible/apartado/no vendible y costo promedio. `repuestos` posee número de parte, fabricante, original/genérico, equivalencias y compatibilidad de marca/modelo/años; referencia el producto común por ID estable. Un kit comercial no tiene stock físico propio: su composición versionada o fotografiada al venderse define cantidades a descontar. No hay ubicaciones físicas.

## Tareas

- [ ] **Catálogo.** Migración de productos, unidades y categorías con códigos únicos por negocio, estados activo/inactivo y cantidades fraccionarias permitidas según unidad. Servicios de alta/edición/búsqueda paginada con validación Pydantic y permiso. Probar duplicados, código vacío, inactivación de producto con historial y búsqueda por nombre/código.
- [ ] **Importación/exportación Excel.** Plantilla documentada con encabezados, tipos y errores por fila; previsualizar y permitir confirmar solo registros válidos o rechazar lote según política explícita del asistente. No duplicar productos por reintento; exportación fiel. Probar archivo corrupto, columnas faltantes, fórmulas inesperadas, mil filas y caracteres acentuados.
- [ ] **Libro de inventario.** Movimientos inmutables para compra, venta, apartado, liberación, devolución y ajuste. Transacción que comprueba disponibilidad antes de confirmar y jamás deja saldo vendible negativo. Ajuste manual exige motivo/permiso/auditoría. Probar rollback ante fallo de la última línea, doble solicitud y concurrencia de tareas.
- [ ] **Costo promedio.** Determinar fórmula y precisión de la especificación monetaria en Core; compras recalculan promedio, ventas guardan costo histórico por línea y no recalculan reportes previos. Probar entradas a distintos costos, cantidades fraccionarias, devolución y stock cero.
- [ ] **Repuestos.** Alta de parte y equivalentes, compatibilidad por marca/modelo/rango de años y búsqueda indexada. Probar parte compartida entre marcas, años de extremos, equivalencia duplicada y producto inactivo. La búsqueda de POS no carga todo el catálogo.
- [ ] **Kits.** Validar componentes activos, cantidades positivas y ausencia de ciclos; calcular disponibilidad como mínimo de componentes, descontarlos atómicamente al vender y guardar fotografía de composición/costo. Probar componente insuficiente y cambio posterior de kit sin alterar venta histórica.
- [ ] **Pantallas.** Formularios y lista paginada con permisos en navegación y servicios; consultas rápidas para 1,000 productos en equipo objetivo, errores legibles y uso por teclado/lector USB tipo teclado.

## Evidencia de salida

Base migrada con datos, consulta y edición visual, export/import de muestra, trazabilidad de cada unidad, saldo reconciliado contra movimientos y venta simulada de kit sin pérdida parcial ante error. Medir búsqueda y render de catálogo en Windows objetivo.
