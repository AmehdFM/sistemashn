-- Upsert de la fila 1:1 opcional de Repuestos.DetalleProducto.
CREATE PROCEDURE Repuestos.sp_GuardarDetalleProducto
    @ProductoId      INT,
    @NumeroParte     NVARCHAR(50) = NULL,
    @MarcaFabricante NVARCHAR(50) = NULL,
    @EsOriginal      BIT = 1,
    @UsuarioId       INT = NULL
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

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoDetalleProducto;

        IF EXISTS (SELECT 1 FROM Repuestos.DetalleProducto WHERE ProductoId = @ProductoId)
        BEGIN
            UPDATE Repuestos.DetalleProducto
            SET NumeroParte     = @NumeroParte,
                MarcaFabricante = @MarcaFabricante,
                EsOriginal      = @EsOriginal
            WHERE ProductoId = @ProductoId;
        END
        ELSE
        BEGIN
            INSERT INTO Repuestos.DetalleProducto (ProductoId, NumeroParte, MarcaFabricante, EsOriginal)
            VALUES (@ProductoId, @NumeroParte, @MarcaFabricante, @EsOriginal);
        END

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@ProductoId AS NVARCHAR(50));

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'GUARDAR_DETALLE_PRODUCTO',
            @TablaAfectada = 'Repuestos.DetalleProducto',
            @RegistroId    = @RegistroIdAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Detalle de producto guardado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoDetalleProducto;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
