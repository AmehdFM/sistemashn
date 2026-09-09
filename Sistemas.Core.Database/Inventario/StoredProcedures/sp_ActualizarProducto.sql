-- ============================================================================
-- Inventario.sp_ActualizarProducto
--
-- Edita un producto ya existente. Nunca toca Codigo (clave natural) ni
-- StockActual (eso solo cambia por Repuestos.sp_RegistrarCompra o
-- Repuestos.sp_RegistrarVenta) — complementa a sp_CrearProducto, que sigue
-- existiendo solo para altas nuevas.
-- ============================================================================
CREATE PROCEDURE Inventario.sp_ActualizarProducto
    @ProductoId     INT,
    @Nombre         NVARCHAR(150),
    @Descripcion    NVARCHAR(500) = NULL,
    @PrecioUnitario DECIMAL(12,2),
    @CategoriaId    INT = NULL,
    @TasaISV        DECIMAL(5,2) = 15.00,
    @StockMinimo    DECIMAL(12,2) = 0,
    @UnidadMedidaId INT = 1,
    @Activo         BIT = 1,
    @UsuarioId      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El producto especificado no existe' AS Mensaje;
            RETURN;
        END

        IF @TasaISV NOT IN (0.00, 15.00, 18.00)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Tasa de ISV inválida (debe ser 0, 15 o 18)' AS Mensaje;
            RETURN;
        END

        IF @CategoriaId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Inventario.Categorias WHERE Id = @CategoriaId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La categoría especificada no existe' AS Mensaje;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Id = @UnidadMedidaId AND Activo = 1)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La unidad de medida especificada no existe o está inactiva' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Id = @UnidadMedidaId AND PermiteFraccion = 0)
           AND @StockMinimo <> ROUND(@StockMinimo, 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Esta unidad de medida no admite cantidades fraccionarias' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoActualizarProducto;

        UPDATE Inventario.Productos
        SET Nombre         = @Nombre,
            Descripcion    = @Descripcion,
            PrecioUnitario = @PrecioUnitario,
            CategoriaId    = @CategoriaId,
            TasaISV        = @TasaISV,
            StockMinimo    = @StockMinimo,
            UnidadMedidaId = @UnidadMedidaId,
            Activo         = @Activo
        WHERE Id = @ProductoId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'ACTUALIZAR_PRODUCTO',
            @TablaAfectada = 'Inventario.Productos',
            @RegistroId    = @ProductoId;

        SELECT CAST(1 AS BIT) AS Exito, 'Producto actualizado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoActualizarProducto;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
