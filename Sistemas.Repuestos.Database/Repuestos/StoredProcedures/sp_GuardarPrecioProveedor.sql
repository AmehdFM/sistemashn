-- Upsert de Repuestos.ProductoProveedor (PK compuesta ProductoId+ProveedorId).
CREATE PROCEDURE Repuestos.sp_GuardarPrecioProveedor
    @ProductoId   INT,
    @ProveedorId  INT,
    @PrecioCompra DECIMAL(12,2),
    @UsuarioId    INT = NULL
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

        IF NOT EXISTS (SELECT 1 FROM Repuestos.Proveedores WHERE Id = @ProveedorId AND Activo = 1)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El proveedor especificado no existe o está inactivo' AS Mensaje;
            RETURN;
        END

        IF @PrecioCompra < 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El precio de compra no puede ser negativo' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoPrecioProveedor;

        IF EXISTS (SELECT 1 FROM Repuestos.ProductoProveedor WHERE ProductoId = @ProductoId AND ProveedorId = @ProveedorId)
        BEGIN
            UPDATE Repuestos.ProductoProveedor
            SET PrecioCompra = @PrecioCompra
            WHERE ProductoId = @ProductoId AND ProveedorId = @ProveedorId;
        END
        ELSE
        BEGIN
            INSERT INTO Repuestos.ProductoProveedor (ProductoId, ProveedorId, PrecioCompra)
            VALUES (@ProductoId, @ProveedorId, @PrecioCompra);
        END

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@ProductoId AS NVARCHAR(50)) + '-' + CAST(@ProveedorId AS NVARCHAR(50));

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'GUARDAR_PRECIO_PROVEEDOR',
            @TablaAfectada = 'Repuestos.ProductoProveedor',
            @RegistroId    = @RegistroIdAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Precio de proveedor guardado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPrecioProveedor;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
