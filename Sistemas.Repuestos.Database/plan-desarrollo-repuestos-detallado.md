# Plan de desarrollo detallado — Sistemas.Repuestos.Database

## Rol de este documento

Especificación completa para construir `Sistemas.Repuestos.Database`. Este proyecto tiene una **referencia "misma base de datos" hacia `Sistemas.Core.Database`** — las tablas de Core (`Inventario.Productos`, `Inventario.Categorias`, `Facturacion.ConfiguracionCAI`, `Security.Usuarios`, etc.) ya existen y se consumen por FK, **nunca se modifican ni se redeclaran acá**.

**Alcance del negocio:** tienda de autopartes que compra a proveedores, revende, arma paquetes/combos, y factura con CAI. Sin reportes avanzados — solo operación + import/export Excel (ya cubierto por `Inventario.sp_ImportarProductosMasivo` de Core).

**Schema de este proyecto:** `Repuestos` — todo objeto nuevo va ahí, nunca en `dbo` ni en los schemas de Core.

**Regla central (igual que en Core):** lógica de negocio en el SP, nunca en la app. Transacción con rollback en toda operación que toque más de una tabla. Resultado explícito de éxito/error en cada SP.

---

## Orden de construcción

1. `Repuestos` — extensión de catálogo (DetalleProducto, VehiculoCompatible, NumeroEquivalente)
2. `Repuestos` — Proveedores
3. `Repuestos` — Compras (depende de Proveedores y de Productos de Core)
4. `Repuestos` — Paquetes (depende de Productos de Core)
5. `Repuestos` — Ventas (depende de Paquetes, Productos, y de `Facturacion` de Core)

---

## 1. Extensión de catálogo

```sql
CREATE SCHEMA Repuestos;
GO

CREATE TABLE Repuestos.DetalleProducto (
    ProductoId      INT             NOT NULL PRIMARY KEY,
    NumeroParte     NVARCHAR(50)    NULL,
    MarcaFabricante NVARCHAR(50)    NULL,
    EsOriginal      BIT             NOT NULL DEFAULT 1,
    CONSTRAINT FK_DetalleProducto_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id)
);
GO
```

**Nota:** es una extensión **opcional** 1:1 — no todo producto de Repuestos necesariamente tiene esta fila (ej. un insumo genérico como grasa o trapos no tiene "número de parte"). Los `Services` del lado .NET deben usar `LEFT JOIN`, no `INNER JOIN`, al consultarla.

```sql
CREATE TABLE Repuestos.VehiculoCompatible (
    Id          INT             IDENTITY(1,1) PRIMARY KEY,
    ProductoId  INT             NOT NULL,
    Marca       NVARCHAR(50)    NOT NULL,
    Modelo      NVARCHAR(50)    NOT NULL,
    AnioDesde   SMALLINT        NOT NULL,
    AnioHasta   SMALLINT        NOT NULL,
    CONSTRAINT FK_VehiculoCompatible_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_VehiculoCompatible_Anios CHECK (AnioHasta >= AnioDesde),
    CONSTRAINT CK_VehiculoCompatible_AnioDesde_Rango CHECK (AnioDesde BETWEEN 1950 AND YEAR(GETDATE()) + 1),
    CONSTRAINT UQ_VehiculoCompatible UNIQUE (ProductoId, Marca, Modelo, AnioDesde, AnioHasta)
);
GO

CREATE INDEX IX_VehiculoCompatible_MarcaModelo ON Repuestos.VehiculoCompatible(Marca, Modelo);
CREATE INDEX IX_VehiculoCompatible_ProductoId ON Repuestos.VehiculoCompatible(ProductoId);
GO

CREATE TABLE Repuestos.NumeroEquivalente (
    Id          INT             IDENTITY(1,1) PRIMARY KEY,
    ProductoId  INT             NOT NULL,
    NumeroOEM   NVARCHAR(50)    NOT NULL,
    Fabricante  NVARCHAR(50)    NULL,
    CONSTRAINT FK_NumeroEquivalente_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT UQ_NumeroEquivalente UNIQUE (ProductoId, NumeroOEM)
);
GO

CREATE INDEX IX_NumeroEquivalente_NumeroOEM ON Repuestos.NumeroEquivalente(NumeroOEM);
GO
```

**Por qué el índice en `NumeroOEM`:** el caso de uso típico es "el cliente trae un número de parte de otro fabricante, ¿qué tengo yo que sirva?" — esa búsqueda tiene que ser rápida, de ahí el índice dedicado.

---

## 2. Proveedores

```sql
CREATE TABLE Repuestos.Proveedores (
    Id          INT             IDENTITY(1,1) PRIMARY KEY,
    Nombre      NVARCHAR(150)   NOT NULL,
    RTN         CHAR(14)        NULL,
    Telefono    NVARCHAR(20)    NULL,
    Contacto    NVARCHAR(100)   NULL,
    Activo      BIT             NOT NULL DEFAULT 1,
    CONSTRAINT UQ_Proveedores_Nombre UNIQUE (Nombre),
    CONSTRAINT CK_Proveedores_RTN CHECK (RTN IS NULL OR (LEN(RTN) = 14 AND RTN NOT LIKE '%[^0-9]%'))
);
GO

CREATE TABLE Repuestos.ProductoProveedor (
    ProductoId      INT             NOT NULL,
    ProveedorId     INT             NOT NULL,
    PrecioCompra    DECIMAL(12,2)   NOT NULL,
    CONSTRAINT PK_ProductoProveedor PRIMARY KEY (ProductoId, ProveedorId),
    CONSTRAINT FK_ProductoProveedor_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT FK_ProductoProveedor_Proveedores FOREIGN KEY (ProveedorId) REFERENCES Repuestos.Proveedores(Id),
    CONSTRAINT CK_ProductoProveedor_Precio CHECK (PrecioCompra >= 0)
);
GO
```

---

## 3. Compras (incrementan stock)

```sql
CREATE TABLE Repuestos.Compras (
    Id                      INT             IDENTITY(1,1) PRIMARY KEY,
    ProveedorId             INT             NOT NULL,
    NumeroFacturaProveedor  NVARCHAR(30)    NULL,
    Fecha                   DATETIME2(0)    NOT NULL DEFAULT SYSDATETIME(),
    Total                   DECIMAL(12,2)   NOT NULL DEFAULT 0,
    UsuarioId               INT             NOT NULL,
    EsCredito               BIT             NOT NULL DEFAULT 0,
    CONSTRAINT FK_Compras_Proveedores FOREIGN KEY (ProveedorId) REFERENCES Repuestos.Proveedores(Id),
    CONSTRAINT FK_Compras_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_Compras_Total CHECK (Total >= 0)
);
GO

CREATE TABLE Repuestos.CompraDetalle (
    Id              INT             IDENTITY(1,1) PRIMARY KEY,
    CompraId        INT             NOT NULL,
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL,
    Subtotal        AS (Cantidad * CostoUnitario) PERSISTED,
    CONSTRAINT FK_CompraDetalle_Compras FOREIGN KEY (CompraId) REFERENCES Repuestos.Compras(Id),
    CONSTRAINT FK_CompraDetalle_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_CompraDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_CompraDetalle_Costo CHECK (CostoUnitario >= 0)
);
GO

CREATE TYPE Repuestos.CompraDetalleTableType AS TABLE (
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL
);
GO
```

**`Subtotal` como columna calculada (`PERSISTED`):** se guarda físicamente y se recalcula sola cada vez que cambian `Cantidad` o `CostoUnitario` — evita que un `INSERT` mal armado desde la app guarde un subtotal inconsistente con sus propios valores.

### `Repuestos.sp_RegistrarCompra`

```sql
CREATE PROCEDURE Repuestos.sp_RegistrarCompra
    @ProveedorId            INT,
    @NumeroFacturaProveedor NVARCHAR(30) = NULL,
    @UsuarioId              INT,
    @EsCredito              BIT = 0,
    @DiasCredito            INT = NULL,   -- ej. 30; solo se usa si @EsCredito = 1
    @Detalle                Repuestos.CompraDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Repuestos.Proveedores WHERE Id = @ProveedorId AND Activo = 1)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Proveedor no válido o inactivo' AS Mensaje, NULL AS CompraId;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM @Detalle)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La compra debe tener al menos un producto' AS Mensaje, NULL AS CompraId;
            RETURN;
        END

        BEGIN TRAN;

        DECLARE @CompraId INT;
        DECLARE @Total DECIMAL(12,2) = (SELECT SUM(Cantidad * CostoUnitario) FROM @Detalle);

        INSERT INTO Repuestos.Compras (ProveedorId, NumeroFacturaProveedor, Total, UsuarioId, EsCredito)
        VALUES (@ProveedorId, @NumeroFacturaProveedor, @Total, @UsuarioId, @EsCredito);

        SET @CompraId = SCOPE_IDENTITY();

        INSERT INTO Repuestos.CompraDetalle (CompraId, ProductoId, Cantidad, CostoUnitario)
        SELECT @CompraId, ProductoId, Cantidad, CostoUnitario FROM @Detalle;

        -- Incrementa stock de forma set-based (una sola sentencia, no un loop fila por fila)
        UPDATE p
        SET p.StockActual = p.StockActual + d.Cantidad
        FROM Inventario.Productos p
        INNER JOIN @Detalle d ON d.ProductoId = p.Id;

        IF @EsCredito = 1
        BEGIN
            INSERT INTO Repuestos.CuentasPorPagar (CompraId, MontoOriginal, SaldoPendiente, FechaVencimiento)
            VALUES (@CompraId, @Total, @Total, DATEADD(DAY, ISNULL(@DiasCredito, 30), CAST(GETDATE() AS DATE)));
        END

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'COMPRA_REGISTRADA',
            @TablaAfectada = 'Repuestos.Compras',
            @RegistroId = @CompraId;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Compra registrada' AS Mensaje, @CompraId AS CompraId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS CompraId;
    END CATCH
END
```

**Nota de orden:** la tabla `Repuestos.CuentasPorPagar` se define más abajo (sección 6) — en SSDT esto no es un problema, SQL Server resuelve las referencias entre objetos del mismo proyecto al momento de compilar, no en el orden en que aparecen los archivos.

**Por qué el `UPDATE ... FROM ... JOIN` en vez de un cursor/loop:** actualizar el stock de 20 productos de una compra en una sola sentencia `UPDATE` es más rápido y más simple de razonar que iterar fila por fila — SQL Server está optimizado para operaciones por conjunto, no por fila.

---

## 4. Paquetes (combos)

```sql
CREATE TABLE Repuestos.Paquetes (
    ProductoId  INT NOT NULL PRIMARY KEY,
    CONSTRAINT FK_Paquetes_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id)
);
GO

CREATE TABLE Repuestos.PaqueteDetalle (
    Id                      INT             IDENTITY(1,1) PRIMARY KEY,
    PaqueteId               INT             NOT NULL,
    ComponenteProductoId    INT             NOT NULL,
    Cantidad                INT             NOT NULL,
    CONSTRAINT FK_PaqueteDetalle_Paquetes FOREIGN KEY (PaqueteId) REFERENCES Repuestos.Paquetes(ProductoId),
    CONSTRAINT FK_PaqueteDetalle_Productos FOREIGN KEY (ComponenteProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_PaqueteDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_PaqueteDetalle_NoAutoReferencia CHECK (ComponenteProductoId <> PaqueteId),
    CONSTRAINT UQ_PaqueteDetalle UNIQUE (PaqueteId, ComponenteProductoId)
);
GO

CREATE TYPE Repuestos.PaqueteDetalleTableType AS TABLE (
    ComponenteProductoId    INT NOT NULL,
    Cantidad                INT NOT NULL
);
GO
```

**Importante — algo que un `CHECK` no puede validar y hay que resolver en el SP:** SQL Server no permite que un `CHECK` consulte otra tabla, así que la regla **"un componente no puede ser a su vez otro paquete" (evitar paquetes anidados)** se valida en `sp_ArmarPaquete`, no en la tabla.

### `Repuestos.sp_ArmarPaquete`

```sql
CREATE PROCEDURE Repuestos.sp_ArmarPaquete
    @ProductoIdPaquete  INT,
    @UsuarioId          INT,
    @Componentes        Repuestos.PaqueteDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El producto del paquete no existe — crearlo primero con sp_CrearProducto' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes c INNER JOIN Repuestos.Paquetes p ON p.ProductoId = c.ComponenteProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'No se permiten paquetes anidados: un componente no puede ser otro paquete' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes WHERE ComponenteProductoId = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El paquete no puede contenerse a sí mismo' AS Mensaje;
            RETURN;
        END

        BEGIN TRAN;

        IF NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes WHERE ProductoId = @ProductoIdPaquete)
            INSERT INTO Repuestos.Paquetes (ProductoId) VALUES (@ProductoIdPaquete);
        ELSE
            DELETE FROM Repuestos.PaqueteDetalle WHERE PaqueteId = @ProductoIdPaquete; -- rearmar desde cero si ya existía

        INSERT INTO Repuestos.PaqueteDetalle (PaqueteId, ComponenteProductoId, Cantidad)
        SELECT @ProductoIdPaquete, ComponenteProductoId, Cantidad FROM @Componentes;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'PAQUETE_ARMADO',
            @TablaAfectada = 'Repuestos.Paquetes', @RegistroId = @ProductoIdPaquete;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Paquete armado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
```

---

## 5. Ventas (usa Facturación de Core, decrementa stock, expande paquetes)

```sql
CREATE TABLE Repuestos.Ventas (
    Id              INT             IDENTITY(1,1) PRIMARY KEY,
    NumeroFactura   NVARCHAR(60)    NOT NULL,
    Fecha           DATETIME2(0)    NOT NULL DEFAULT SYSDATETIME(),
    Subtotal        DECIMAL(12,2)   NOT NULL,
    MontoISV        DECIMAL(12,2)   NOT NULL,
    Total           DECIMAL(12,2)   NOT NULL,
    UsuarioId       INT             NOT NULL,
    EsCredito       BIT             NOT NULL DEFAULT 0,
    Anulada         BIT             NOT NULL DEFAULT 0,
    MotivoAnulacion NVARCHAR(200)   NULL,
    CONSTRAINT UQ_Ventas_NumeroFactura UNIQUE (NumeroFactura),
    CONSTRAINT FK_Ventas_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_Ventas_Subtotal CHECK (Subtotal >= 0),
    CONSTRAINT CK_Ventas_MontoISV CHECK (MontoISV >= 0),
    CONSTRAINT CK_Ventas_Total CHECK (Total >= 0)
);
GO

CREATE TABLE Repuestos.VentaDetalle (
    Id              INT             IDENTITY(1,1) PRIMARY KEY,
    VentaId         INT             NOT NULL,
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    PrecioUnitario  DECIMAL(12,2)   NOT NULL,   -- snapshot del precio al momento de vender, no se recalcula si el precio cambia después
    Subtotal        AS (Cantidad * PrecioUnitario) PERSISTED,
    CONSTRAINT FK_VentaDetalle_Ventas FOREIGN KEY (VentaId) REFERENCES Repuestos.Ventas(Id),
    CONSTRAINT FK_VentaDetalle_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_VentaDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_VentaDetalle_Precio CHECK (PrecioUnitario >= 0)
);
GO

CREATE TYPE Repuestos.VentaDetalleTableType AS TABLE (
    ProductoId  INT NOT NULL,
    Cantidad    INT NOT NULL
);
GO
```

**Por qué `PrecioUnitario` se guarda en el detalle en vez de leerlo siempre de `Productos`:** si el precio de un producto cambia el mes que viene, las facturas ya emitidas no deben cambiar de valor retroactivamente — es una "fotografía" del precio al momento de la venta, requisito básico de cualquier sistema de facturación.

**Por qué `Anulada` en vez de `DELETE`:** una factura con CAI ya emitida no se puede borrar — el correlativo queda "quemado" aunque se anule. Se marca `Anulada = 1` con su motivo, nunca se elimina la fila. *(Recomendación: que confirmen el procedimiento exacto de anulación con su contador/asesor fiscal — el principio de no reutilizar el correlativo es general, pero el detalle formal de cómo debe quedar registrada una anulación ante el SAR conviene validarlo con alguien que maneje el tema tributario actualizado, no asumirlo solo desde acá.)*

### `Repuestos.sp_RegistrarVenta`

**Lógica clave a entender antes de leer el código:** el cliente puede comprar un producto normal o un **paquete**. Lo que se guarda en `VentaDetalle` es exactamente lo que el cliente compró (si compró un paquete, se guarda una línea con el paquete). Pero el **stock que se descuenta** es el de los **componentes individuales** del paquete, no del paquete en sí (el paquete no tiene stock propio). Por eso el SP arma una tabla temporal "expandida" solo para el descuento de inventario.

```sql
CREATE PROCEDURE Repuestos.sp_RegistrarVenta
    @UsuarioId      INT,
    @EsCredito      BIT = 0,
    @DiasCredito    INT = NULL,   -- ej. 15/30; solo se usa si @EsCredito = 1
    @Detalle        Repuestos.VentaDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM @Detalle)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La venta debe tener al menos un producto' AS Mensaje, NULL AS NumeroFactura, NULL AS Total;
            RETURN;
        END

        -- 1. Expandir paquetes a sus componentes reales, en una tabla temporal
        DECLARE @StockRequerido TABLE (ProductoId INT PRIMARY KEY, CantidadRequerida INT);

        INSERT INTO @StockRequerido (ProductoId, CantidadRequerida)
        SELECT ProductoId, SUM(CantidadRequerida) FROM (
            -- líneas que NO son paquete: se descuentan tal cual
            SELECT d.ProductoId, d.Cantidad AS CantidadRequerida
            FROM @Detalle d
            WHERE NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes pq WHERE pq.ProductoId = d.ProductoId)

            UNION ALL

            -- líneas que SÍ son paquete: se expanden a sus componentes
            SELECT pd.ComponenteProductoId AS ProductoId, pd.Cantidad * d.Cantidad AS CantidadRequerida
            FROM @Detalle d
            INNER JOIN Repuestos.PaqueteDetalle pd ON pd.PaqueteId = d.ProductoId
        ) expandido
        GROUP BY ProductoId;

        -- 2. Validar stock suficiente ANTES de tocar nada
        IF EXISTS (
            SELECT 1 FROM @StockRequerido sr
            INNER JOIN Inventario.Productos p ON p.Id = sr.ProductoId
            WHERE p.StockActual < sr.CantidadRequerida
        )
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Stock insuficiente para completar la venta' AS Mensaje, NULL AS NumeroFactura, NULL AS Total;
            RETURN;
        END

        BEGIN TRAN;

        -- 3. Obtener correlativo CAI (de Core) — si falla (vencido/agotado), se aborta todo
        DECLARE @ResultadoCAI TABLE (Exito BIT, Mensaje NVARCHAR(200), Correlativo NVARCHAR(60));
        INSERT INTO @ResultadoCAI EXEC Facturacion.sp_ObtenerCorrelativoCAI;

        DECLARE @Correlativo NVARCHAR(60) = (SELECT Correlativo FROM @ResultadoCAI);
        IF (SELECT Exito FROM @ResultadoCAI) = 0
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, (SELECT Mensaje FROM @ResultadoCAI) AS Mensaje, NULL AS NumeroFactura, NULL AS Total;
            RETURN;
        END

        -- 4. Calcular montos usando precio y tasa ISV vigentes de cada producto vendido (no de los componentes expandidos)
        DECLARE @Subtotal DECIMAL(12,2), @MontoISV DECIMAL(12,2);

        SELECT
            @Subtotal = SUM(d.Cantidad * p.PrecioUnitario),
            @MontoISV = SUM(Facturacion.fn_CalcularISV(d.Cantidad * p.PrecioUnitario, p.TasaISV))
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId;

        DECLARE @VentaId INT;

        INSERT INTO Repuestos.Ventas (NumeroFactura, Subtotal, MontoISV, Total, UsuarioId, EsCredito)
        VALUES (@Correlativo, @Subtotal, @MontoISV, @Subtotal + @MontoISV, @UsuarioId, @EsCredito);

        SET @VentaId = SCOPE_IDENTITY();

        IF @EsCredito = 1
        BEGIN
            INSERT INTO Repuestos.CuentasPorCobrar (VentaId, MontoOriginal, SaldoPendiente, FechaVencimiento)
            VALUES (@VentaId, @Subtotal + @MontoISV, @Subtotal + @MontoISV, DATEADD(DAY, ISNULL(@DiasCredito, 15), CAST(GETDATE() AS DATE)));
        END

        INSERT INTO Repuestos.VentaDetalle (VentaId, ProductoId, Cantidad, PrecioUnitario)
        SELECT @VentaId, d.ProductoId, d.Cantidad, p.PrecioUnitario
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId;

        -- 5. Descontar stock de los componentes YA EXPANDIDOS (set-based)
        UPDATE p
        SET p.StockActual = p.StockActual - sr.CantidadRequerida
        FROM Inventario.Productos p
        INNER JOIN @StockRequerido sr ON sr.ProductoId = p.Id;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'VENTA_REGISTRADA',
            @TablaAfectada = 'Repuestos.Ventas', @RegistroId = @VentaId, @Detalle = @Correlativo;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Venta registrada' AS Mensaje, @Correlativo AS NumeroFactura, (@Subtotal + @MontoISV) AS Total;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS NumeroFactura, NULL AS Total;
    END CATCH
END
```

**Por qué se valida el stock ANTES de `BEGIN TRAN` y de pedir el correlativo CAI:** pedir un correlativo cuesta "quemar" un número de factura — no querés consumir un número del rango autorizado para una venta que de todas formas iba a fallar por falta de stock. Por eso el chequeo de stock ocurre primero, fuera de la transacción principal, y solo si pasa se entra a la transacción real donde sí se pide el CAI.

### `Repuestos.sp_AnularVenta`

```sql
CREATE PROCEDURE Repuestos.sp_AnularVenta
    @VentaId    INT,
    @UsuarioId  INT,
    @Motivo     NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Repuestos.Ventas WHERE Id = @VentaId AND Anulada = 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Venta no encontrada o ya estaba anulada' AS Mensaje;
            RETURN;
        END

        BEGIN TRAN;

        -- Restaurar stock: mismo cálculo de expansión de paquetes que en sp_RegistrarVenta
        DECLARE @StockDevuelto TABLE (ProductoId INT PRIMARY KEY, Cantidad INT);

        INSERT INTO @StockDevuelto (ProductoId, Cantidad)
        SELECT ProductoId, SUM(Cantidad) FROM (
            SELECT vd.ProductoId, vd.Cantidad
            FROM Repuestos.VentaDetalle vd
            WHERE vd.VentaId = @VentaId
              AND NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes pq WHERE pq.ProductoId = vd.ProductoId)

            UNION ALL

            SELECT pd.ComponenteProductoId, pd.Cantidad * vd.Cantidad
            FROM Repuestos.VentaDetalle vd
            INNER JOIN Repuestos.PaqueteDetalle pd ON pd.PaqueteId = vd.ProductoId
            WHERE vd.VentaId = @VentaId
        ) expandido
        GROUP BY ProductoId;

        UPDATE p
        SET p.StockActual = p.StockActual + sd.Cantidad
        FROM Inventario.Productos p
        INNER JOIN @StockDevuelto sd ON sd.ProductoId = p.Id;

        UPDATE Repuestos.Ventas
        SET Anulada = 1, MotivoAnulacion = @Motivo
        WHERE Id = @VentaId;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'VENTA_ANULADA',
            @TablaAfectada = 'Repuestos.Ventas', @RegistroId = @VentaId, @Detalle = @Motivo;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Venta anulada, stock restaurado' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
```

### `Repuestos.sp_ObtenerProductoRepuesto`

**Parámetro:** `@ProductoId INT`.
**Lógica:** devuelve **tres result sets** en una sola llamada (Dapper los lee con `QueryMultipleAsync`):
1. Datos base del producto (`Inventario.Productos` `LEFT JOIN Repuestos.DetalleProducto`)
2. Todos los vehículos compatibles (`Repuestos.VehiculoCompatible WHERE ProductoId = @ProductoId`)
3. Todos los números OEM equivalentes (`Repuestos.NumeroEquivalente WHERE ProductoId = @ProductoId`)

```sql
CREATE PROCEDURE Repuestos.sp_ObtenerProductoRepuesto
    @ProductoId INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT p.Id, p.Codigo, p.Nombre, p.Descripcion, p.PrecioUnitario, p.StockActual,
           dp.NumeroParte, dp.MarcaFabricante, dp.EsOriginal
    FROM Inventario.Productos p
    LEFT JOIN Repuestos.DetalleProducto dp ON dp.ProductoId = p.Id
    WHERE p.Id = @ProductoId;

    SELECT Marca, Modelo, AnioDesde, AnioHasta
    FROM Repuestos.VehiculoCompatible
    WHERE ProductoId = @ProductoId;

    SELECT NumeroOEM, Fabricante
    FROM Repuestos.NumeroEquivalente
    WHERE ProductoId = @ProductoId;
END
```

---

## 6. Cuentas por cobrar y por pagar

**Alcance:** control de crédito básico — saldo pendiente por venta/compra a crédito, pagos parciales, vencimiento. No es un módulo contable completo (sin libro mayor, sin partida doble) — eso excede el alcance de "sistema simple" ya definido.

```sql
CREATE TABLE Repuestos.CuentasPorCobrar (
    Id                  INT             IDENTITY(1,1) PRIMARY KEY,
    VentaId             INT             NOT NULL,
    MontoOriginal       DECIMAL(12,2)   NOT NULL,
    SaldoPendiente      DECIMAL(12,2)   NOT NULL,
    FechaVencimiento    DATE            NOT NULL,
    Estado              NVARCHAR(20)    NOT NULL DEFAULT 'Pendiente',
    CONSTRAINT UQ_CuentasPorCobrar_VentaId UNIQUE (VentaId),
    CONSTRAINT FK_CuentasPorCobrar_Ventas FOREIGN KEY (VentaId) REFERENCES Repuestos.Ventas(Id),
    CONSTRAINT CK_CuentasPorCobrar_Montos CHECK (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal),
    CONSTRAINT CK_CuentasPorCobrar_Estado CHECK (Estado IN ('Pendiente', 'PagadaParcial', 'Pagada'))
);
GO

CREATE TABLE Repuestos.PagoCuentaPorCobrar (
    Id                  INT             IDENTITY(1,1) PRIMARY KEY,
    CuentaPorCobrarId   INT             NOT NULL,
    Monto               DECIMAL(12,2)   NOT NULL,
    Fecha               DATETIME2(0)    NOT NULL DEFAULT SYSDATETIME(),
    MetodoPago          NVARCHAR(30)    NULL,
    UsuarioId           INT             NOT NULL,
    CONSTRAINT FK_PagoCPC_CuentaPorCobrar FOREIGN KEY (CuentaPorCobrarId) REFERENCES Repuestos.CuentasPorCobrar(Id),
    CONSTRAINT FK_PagoCPC_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_PagoCPC_Monto CHECK (Monto > 0)
);
GO

CREATE TABLE Repuestos.CuentasPorPagar (
    Id                  INT             IDENTITY(1,1) PRIMARY KEY,
    CompraId            INT             NOT NULL,
    MontoOriginal       DECIMAL(12,2)   NOT NULL,
    SaldoPendiente      DECIMAL(12,2)   NOT NULL,
    FechaVencimiento    DATE            NOT NULL,
    Estado              NVARCHAR(20)    NOT NULL DEFAULT 'Pendiente',
    CONSTRAINT UQ_CuentasPorPagar_CompraId UNIQUE (CompraId),
    CONSTRAINT FK_CuentasPorPagar_Compras FOREIGN KEY (CompraId) REFERENCES Repuestos.Compras(Id),
    CONSTRAINT CK_CuentasPorPagar_Montos CHECK (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal),
    CONSTRAINT CK_CuentasPorPagar_Estado CHECK (Estado IN ('Pendiente', 'PagadaParcial', 'Pagada'))
);
GO

CREATE TABLE Repuestos.PagoCuentaPorPagar (
    Id                  INT             IDENTITY(1,1) PRIMARY KEY,
    CuentaPorPagarId    INT             NOT NULL,
    Monto               DECIMAL(12,2)   NOT NULL,
    Fecha               DATETIME2(0)    NOT NULL DEFAULT SYSDATETIME(),
    MetodoPago          NVARCHAR(30)    NULL,
    UsuarioId           INT             NOT NULL,
    CONSTRAINT FK_PagoCPP_CuentaPorPagar FOREIGN KEY (CuentaPorPagarId) REFERENCES Repuestos.CuentasPorPagar(Id),
    CONSTRAINT FK_PagoCPP_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_PagoCPP_Monto CHECK (Monto > 0)
);
GO
```

**Por qué `Estado` no incluye `'Vencida'` como valor guardado:** si lo guardáramos como estado fijo, necesitaríamos un proceso programado (similar al de backups) que revise diariamente y actualice cuentas vencidas — complejidad extra e innecesaria. En cambio, "vencida" se calcula al momento de **consultar** (`SaldoPendiente > 0 AND FechaVencimiento < GETDATE()`), nunca queda un dato desactualizado guardado en la tabla esperando que un job lo corrija.

### `Repuestos.sp_RegistrarPagoCuentaPorCobrar`

```sql
CREATE PROCEDURE Repuestos.sp_RegistrarPagoCuentaPorCobrar
    @CuentaPorCobrarId INT,
    @Monto             DECIMAL(12,2),
    @MetodoPago        NVARCHAR(30) = NULL,
    @UsuarioId         INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        DECLARE @SaldoActual DECIMAL(12,2);
        SELECT @SaldoActual = SaldoPendiente FROM Repuestos.CuentasPorCobrar WHERE Id = @CuentaPorCobrarId;

        IF @SaldoActual IS NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Cuenta por cobrar no encontrada' AS Mensaje;
            RETURN;
        END

        IF @Monto > @SaldoActual
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El pago excede el saldo pendiente' AS Mensaje;
            RETURN;
        END

        BEGIN TRAN;

        INSERT INTO Repuestos.PagoCuentaPorCobrar (CuentaPorCobrarId, Monto, MetodoPago, UsuarioId)
        VALUES (@CuentaPorCobrarId, @Monto, @MetodoPago, @UsuarioId);

        UPDATE Repuestos.CuentasPorCobrar
        SET SaldoPendiente = SaldoPendiente - @Monto,
            Estado = CASE
                        WHEN SaldoPendiente - @Monto = 0 THEN 'Pagada'
                        ELSE 'PagadaParcial'
                     END
        WHERE Id = @CuentaPorCobrarId;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'PAGO_CXC_REGISTRADO',
            @TablaAfectada = 'Repuestos.CuentasPorCobrar', @RegistroId = @CuentaPorCobrarId;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Pago registrado' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
```

### `Repuestos.sp_RegistrarPagoCuentaPorPagar`

Misma lógica exacta que `sp_RegistrarPagoCuentaPorCobrar`, pero sobre `Repuestos.CuentasPorPagar` / `Repuestos.PagoCuentaPorPagar` y con acción de auditoría `'PAGO_CXP_REGISTRADO'`.

### `Repuestos.sp_ListarCuentasPorCobrar` / `sp_ListarCuentasPorPagar`

**Parámetros:** `@SoloConSaldo BIT = 1` (si es 1, excluye las que ya están en `'Pagada'`).
**Lógica:** `SELECT` con columna calculada `EstaVencida = CASE WHEN SaldoPendiente > 0 AND FechaVencimiento < CAST(GETDATE() AS DATE) THEN 1 ELSE 0 END`, para que la pantalla de "cuentas por cobrar/pagar" pueda resaltar las vencidas sin depender de un estado guardado.

**Qué pasa si se anula una venta/compra a crédito que ya tiene pagos:** `sp_AnularVenta` (sección 5) **no contempla esto todavía** — si van a permitir anular una venta a crédito con pagos parciales ya registrados, hay que decidir la regla de negocio antes de implementarlo (¿se cancela la cuenta por cobrar entera? ¿qué pasa con los pagos ya recibidos?). Dejo esto marcado como pendiente de definir, no lo asumo por mi cuenta porque es una decisión de negocio, no técnica.

---

## Resumen de integridad de datos — checklist de revisión final

**Foreign Keys hacia Core (nunca se modifican esas tablas, solo se referencian):**
- `DetalleProducto.ProductoId`, `VehiculoCompatible.ProductoId`, `NumeroEquivalente.ProductoId`, `ProductoProveedor.ProductoId`, `CompraDetalle.ProductoId`, `Paquetes.ProductoId`, `PaqueteDetalle.ComponenteProductoId`, `VentaDetalle.ProductoId` → todos apuntan a `Inventario.Productos(Id)`
- `Compras.UsuarioId`, `Ventas.UsuarioId`, `PagoCuentaPorCobrar.UsuarioId`, `PagoCuentaPorPagar.UsuarioId` → `Security.Usuarios(Id)`

**Foreign Keys internas nuevas (cuentas por cobrar/pagar):**
- `CuentasPorCobrar.VentaId → Ventas.Id` (única por venta — `UNIQUE`)
- `CuentasPorPagar.CompraId → Compras.Id` (única por compra — `UNIQUE`)
- `PagoCuentaPorCobrar.CuentaPorCobrarId → CuentasPorCobrar.Id`
- `PagoCuentaPorPagar.CuentaPorPagarId → CuentasPorPagar.Id`

**Checks de negocio:**
- Cantidades y precios: nunca negativos ni cero donde no corresponde (`Cantidad > 0` en detalles, `>= 0` en montos)
- Años de compatibilidad: `AnioHasta >= AnioDesde`, dentro de rango razonable
- Paquetes: no se contienen a sí mismos, no se permiten paquetes anidados (validado en el SP, no en constraint, porque `CHECK` no puede consultar otra tabla)
- RTN de proveedor: mismo formato de 14 dígitos que en Core, pero opcional (`NULL` permitido)
- Cuentas por cobrar/pagar: `SaldoPendiente` nunca negativo ni mayor al `MontoOriginal`; un pago nunca puede exceder el saldo pendiente (validado en el SP antes de aplicarlo, no solo con `CHECK`)

**Transacciones (dónde son obligatorias):**
- `sp_RegistrarCompra` — inserta encabezado + detalle + incrementa stock + (si es crédito) crea cuenta por pagar
- `sp_RegistrarVenta` — pide correlativo CAI + inserta encabezado + detalle + decrementa stock + (si es crédito) crea cuenta por cobrar
- `sp_ArmarPaquete` — inserta/reemplaza encabezado + detalle del paquete
- `sp_AnularVenta` — restaura stock + marca anulada
- `sp_RegistrarPagoCuentaPorCobrar` / `sp_RegistrarPagoCuentaPorPagar` — inserta pago + actualiza saldo y estado

**Puntos de diseño no obvios, para tener presentes:**
- El stock se valida **antes** de pedir el correlativo CAI (evita "quemar" números de factura en ventas que van a fallar)
- El precio de venta se **congela** en `VentaDetalle.PrecioUnitario` al momento de la venta, no se recalcula después
- Las facturas nunca se borran, solo se anulan (`Anulada = 1`) — confirmar con un asesor fiscal el procedimiento exacto de anulación ante el SAR antes de dar esto por definitivo
- Los `UPDATE` de stock son siempre set-based (una sola sentencia con `JOIN`), nunca un loop fila por fila
