# 04 — Dominio y glosario

Cuando una IA no sabe qué es un CAI, inventa una tabla que no sirve. Este
documento existe para que eso no pase.

---

## 1. Glosario fiscal hondureño

| Término | Qué es | Dónde vive en el sistema |
|---|---|---|
| **SAR** | Servicio de Administración de Rentas: la autoridad tributaria de Honduras | Contexto, no una entidad |
| **CAI** | *Código de Autorización de Impresión*. Cadena de 32 caracteres hexadecimales que el SAR asigna a un rango de correlativos de factura, con fecha límite de emisión | `Facturacion.ConfiguracionCAI` |
| **Correlativo** | Número de factura con formato `000-001-01-00000001`: establecimiento, punto de emisión, tipo de documento y número secuencial | `Repuestos.Ventas.NumeroFactura`, `NVARCHAR(60)` |
| **ISV** | Impuesto Sobre Ventas. Tres tasas vigentes: **0 %** (exento), **15 %** (general), **18 %** (especial: alcohol y tabaco) | `Productos.TasaISV`, `CK ... IN (0.00, 15.00, 18.00)` |
| **RTN** | Registro Tributario Nacional: el identificador fiscal del contribuyente | Datos del negocio en `Configuracion` |
| **Lempira (L.)** | Moneda de Honduras | Se antepone a mano al formato `N2` — **nunca formato `"C"`** |

**Reglas fiscales que el código debe respetar:**

- Un correlativo emitido **jamás se reutiliza**. Una factura no se borra: se
  anula (`Ventas.Anulada = 1` con motivo y fecha).
- El rango de CAI tiene principio, fin y fecha límite. Agotarse o vencer es un
  evento previsible y el sistema debe avisar **antes** de que ocurra.
- Los importes de una factura emitida son una **fotografía**: `VentaDetalle`
  guarda `PrecioUnitario` y `TasaISV` del momento de la venta, de modo que un
  cambio de precio posterior no altera facturas ya emitidas.

## 2. Glosario del rubro de autorepuestos

| Término | Qué significa |
|---|---|
| **Número de parte** | Código del fabricante para la pieza (`DetalleProducto.NumeroParte`) |
| **Número OEM / equivalencia** | Código de **otro** fabricante que sirve para la misma pieza. El caso de uso central del rubro: el cliente llega con un número cualquiera y hay que saber qué del inventario le sirve (`NumeroEquivalente`) |
| **Original vs. genérico** | Si la pieza es del fabricante del vehículo o de un tercero (`DetalleProducto.EsOriginal`). Cambia precio y expectativa del cliente |
| **Compatibilidad** | A qué marca/modelo/rango de años le sirve la pieza (`VehiculoCompatible`). La consulta real es "¿qué tengo para un Corolla 2015?" |
| **Paquete / kit** | Un producto compuesto que se vende como uno solo (kit de frenos) pero descuenta el stock de sus componentes (`Paquetes` + `PaqueteDetalle`) |

## 3. Glosario comercial

| Término | Qué significa |
|---|---|
| **POS** | Pantalla de caja: alta velocidad, teclado primero, para vender rápido |
| **Ventas** | Pantalla de consulta e historial de ventas. **Es un módulo distinto del POS** — se separaron a propósito |
| **Venta al contado / a crédito** | `Ventas.EsCredito`. A crédito genera automáticamente una cuenta por cobrar |
| **CxC — cuenta por cobrar** | Lo que un cliente debe. `MontoOriginal`, `SaldoPendiente`, `FechaVencimiento`, `Estado` |
| **CxP — cuenta por pagar** | Lo que se le debe a un proveedor por una compra a crédito |
| **Anulación** | Revertir una venta sin borrarla: devuelve stock, marca `Anulada = 1`, guarda motivo y fecha. El correlativo queda quemado |
| **Vencida** | **No es un estado guardado.** Se calcula al consultar: `SaldoPendiente > 0 AND FechaVencimiento < hoy`. Express no trae SQL Server Agent para un proceso diario que lo actualice |

## 4. Mapa de esquemas

### Core — `Sistemas.Core.Database`

| Esquema | Tablas | De qué se ocupa |
|---|---|---|
| `Security` | `Usuarios`, `Roles` | Autenticación y autorización. Roles base: `Administrador`, `Usuario` |
| `Configuracion` | `Configuracion`, `HistorialRespaldos`, `VersionEsquema` | Datos del negocio, marca blanca, control de respaldos y de versión de esquema |
| `Auditoria` | `Auditoria` | Bitácora de operaciones. **La única tabla sin techo de crecimiento**: necesita purga |
| `Inventario` | `Productos`, `Categorias`, `UnidadesMedida`, `Etiquetas`, `ProductoEtiqueta` | Catálogo compartido por todas las verticales |
| `Facturacion` | `ConfiguracionCAI` | Rango de CAI y correlativo actual. `fn_CalcularISV` |

### Vertical de autorepuestos — `Sistemas.Repuestos.Database`

| Grupo | Tablas | Notas |
|---|---|---|
| Catálogo extendido | `DetalleProducto`, `NumeroEquivalente`, `VehiculoCompatible` | `DetalleProducto` es 1:1 **opcional** con `Productos`: `ProductoId` es PK y FK a la vez. Un insumo genérico (grasa, trapos) no tiene número de parte, así que **toda consulta la ataca con `LEFT JOIN`, nunca `INNER`** |
| Proveedores | `Proveedores`, `ProductoProveedor` | `ProductoProveedor` permite comparar precios entre proveedores del mismo producto |
| Compras | `Compras`, `CompraDetalle` | Entrada de mercadería. A crédito genera CxP |
| Paquetes | `Paquetes`, `PaqueteDetalle` | Un paquete **es** un producto de `Inventario.Productos` más una fila que lo marca como tal. **No tiene stock propio**: el que se mueve es el de sus componentes |
| Ventas | `Ventas`, `VentaDetalle` | El corazón. `SeqVentaInterna` da un número interno cuando la facturación legal está desactivada |
| Cuentas | `CuentasPorCobrar`, `PagoCuentaPorCobrar`, `CuentasPorPagar`, `PagoCuentaPorPagar` | Crédito de clientes y deuda con proveedores |

## 5. Invariantes del dominio

Reglas que el sistema no puede violar **nunca**, ni por un camino raro. Antes de
tocar un SP, verificá que tu cambio las preserva.

1. **El stock nunca queda negativo.** `CK_Productos_StockActual CHECK (StockActual >= 0)`,
   y además se revalida **con bloqueo dentro de la transacción** en
   `sp_RegistrarVenta` — el chequeo previo, fuera de transacción, es una
   condición de carrera entre dos cajas.
2. **Un correlativo emitido no se reutiliza jamás.**
3. **Una factura no se borra.** Se anula, con motivo y fecha. Los tres campos de
   anulación (`Anulada`, `MotivoAnulacion`, `FechaAnulacion`) se mueven juntos y
   hay un `CHECK` que lo garantiza.
4. **Los precios en el detalle son históricos.** `VentaDetalle` y
   `CompraDetalle` guardan el precio y la tasa del momento.
5. **El saldo de una cuenta nunca excede su monto original ni baja de cero.**
   `CK ... (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal)`.
6. **Un paquete no tiene stock propio.** Venderlo descuenta el stock de sus
   componentes.
7. **Toda operación sobre dinero o inventario es una sola transacción atómica.**
8. **Las filas de catálogo no se borran**, se desactivan (`Activo = 0`).

## 6. Detalles que ya causaron problemas

Estos están comentados en el propio DDL. Conocerlos evita reintroducirlos:

- **Aritmética decimal:** `DECIMAL(12,2) * DECIMAL(12,2)` sube a escala 4 por
  las reglas de SQL Server. Por eso `VentaDetalle.Subtotal` lleva un `CAST`
  explícito de vuelta a `DECIMAL(12,2)`.
- **`GETDATE()` en un `CHECK` no compila:** no es determinística. La validación
  del año tope de `VehiculoCompatible` vive en el SP, no en la tabla.
- **`UnidadesMedida` fuerza `Id = 1`** para "Unidad", porque
  `Productos.UnidadMedidaId` usa `DEFAULT 1` como literal simple.
- **Cantidades decimales:** el stock es `DECIMAL(12,2)`, no `INT`. Se vende
  media galón de pintura y 2.5 quintales de cemento. `UnidadesMedida` tiene
  `PermiteFraccion` para distinguir lo que sí y lo que no.
