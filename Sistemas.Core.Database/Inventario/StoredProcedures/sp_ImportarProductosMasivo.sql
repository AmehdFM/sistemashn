CREATE PROCEDURE Inventario.sp_ImportarProductosMasivo
    @Productos Inventario.ProductoTableType READONLY,
    @UsuarioId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRAN;

        MERGE Inventario.Productos AS destino
        USING @Productos AS origen
        ON destino.Codigo = origen.Codigo
        WHEN MATCHED THEN
            UPDATE SET
                Nombre          = origen.Nombre,
                Descripcion     = origen.Descripcion,
                PrecioUnitario  = origen.PrecioUnitario,
                CategoriaId     = origen.CategoriaId,
                TasaISV         = ISNULL(origen.TasaISV, destino.TasaISV),
                StockMinimo     = ISNULL(origen.StockMinimo, destino.StockMinimo)
        WHEN NOT MATCHED THEN
            INSERT (Codigo, Nombre, Descripcion, PrecioUnitario, CategoriaId, TasaISV, StockMinimo)
            VALUES (origen.Codigo, origen.Nombre, origen.Descripcion, origen.PrecioUnitario,
                    origen.CategoriaId, ISNULL(origen.TasaISV, 15.00), ISNULL(origen.StockMinimo, 0));

        DECLARE @FilasAfectadas INT = @@ROWCOUNT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'IMPORTACION_MASIVA_PRODUCTOS',
            @TablaAfectada = 'Inventario.Productos',
            @Detalle = @FilasAfectadas;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Importación completada' AS Mensaje, @FilasAfectadas AS FilasAfectadas;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, 0 AS FilasAfectadas;
    END CATCH
END
GO
