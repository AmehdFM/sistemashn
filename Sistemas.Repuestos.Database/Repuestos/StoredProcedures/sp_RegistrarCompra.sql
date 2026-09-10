-- Defecto B-4 corregido: el incremento de stock agrupa el TVP por ProductoId
-- ANTES del UPDATE. Sin el GROUP BY, un UPDATE ... FROM ... JOIN aplica una
-- sola vez cuando el mismo producto aparece en dos líneas del documento
-- (el caso normal de "me llegaron 10 filtros en una caja y 5 en otra"),
-- y el resto se pierde en silencio.
CREATE PROCEDURE Repuestos.sp_RegistrarCompra
    @ProveedorId            INT,
    @NumeroFacturaProveedor NVARCHAR(30) = NULL,
    @UsuarioId              INT,
    @EsCredito              BIT = 0,
    @DiasCredito            INT = NULL,
    @Detalle                Repuestos.CompraDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;
    DECLARE @CompraId INT, @Total DECIMAL(12,2), @ProductoInvalido NVARCHAR(30);

    BEGIN TRY
        ---------- Validaciones previas (fuera de transacción, regla C-6) ----------
        IF NOT EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Id = @ProveedorId AND Activo = 1)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Proveedor no válido o inactivo' AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM @Detalle)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La compra debe tener al menos un producto' AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Detalle WHERE Cantidad <= 0 OR CostoUnitario < 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'Hay líneas con cantidad menor o igual a cero, o costo negativo' AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        SELECT TOP (1) @ProductoInvalido = CAST(d.ProductoId AS NVARCHAR(30))
        FROM @Detalle d
        WHERE NOT EXISTS (SELECT 1 FROM Inventario.Productos p WHERE p.Id = d.ProductoId);

        IF @ProductoInvalido IS NOT NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('El producto con Id ', @ProductoInvalido, ' no existe') AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        -- La unidad de medida del producto (ej. "Unidad") puede exigir
        -- cantidades enteras aunque la columna sea DECIMAL(12,2) para todos.
        SELECT TOP (1) @ProductoInvalido = p.Codigo
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId
        INNER JOIN Inventario.UnidadesMedida um ON um.Id = p.UnidadMedidaId
        WHERE um.PermiteFraccion = 0 AND d.Cantidad <> ROUND(d.Cantidad, 0);

        IF @ProductoInvalido IS NOT NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('El producto ', @ProductoInvalido, ' usa una unidad que no admite cantidades fraccionarias') AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        SET @Total = (SELECT SUM(Cantidad * CostoUnitario) FROM @Detalle);

        ---------- Transacción ----------
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCompra;

        INSERT INTO Repuestos.Compras (ProveedorId, NumeroFacturaProveedor, Total, UsuarioId, EsCredito)
        VALUES (@ProveedorId, @NumeroFacturaProveedor, @Total, @UsuarioId, @EsCredito);

        SET @CompraId = SCOPE_IDENTITY();

        -- El detalle se guarda tal cual viene: cada línea del documento se conserva.
        INSERT INTO Repuestos.CompraDetalle (CompraId, ProductoId, Cantidad, CostoUnitario)
        SELECT @CompraId, ProductoId, Cantidad, CostoUnitario FROM @Detalle;

        -- Defecto B-4: el stock SÍ se agrupa. Sin el GROUP BY, un producto que
        -- aparece en dos líneas incrementa una sola vez y el resto se pierde en silencio.
        UPDATE p
        SET p.StockActual = p.StockActual + d.Cantidad
        FROM Inventario.Productos p
        INNER JOIN (SELECT ProductoId, SUM(Cantidad) AS Cantidad
                    FROM @Detalle
                    GROUP BY ProductoId) d ON d.ProductoId = p.Id;

        IF @EsCredito = 1
        BEGIN
            INSERT INTO Repuestos.CuentasPorPagar (CompraId, MontoOriginal, SaldoPendiente, FechaVencimiento)
            VALUES (@CompraId, @Total, @Total,
                    DATEADD(DAY, ISNULL(@DiasCredito, 30), CAST(SYSDATETIME() AS DATE)));
        END

        IF @TranPropia = 1 COMMIT;

        -- Auditoría DESPUÉS del commit (defecto B-9): si falla, la compra ya está guardada.
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'COMPRA_REGISTRADA',
            @TablaAfectada = 'Repuestos.Compras',
            @RegistroId = @CompraId, @Detalle = @NumeroFacturaProveedor;

        SELECT CAST(1 AS BIT) AS Exito, 'Compra registrada' AS Mensaje, @CompraId AS CompraId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCompra;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS CompraId;
    END CATCH
END
GO
