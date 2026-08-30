CREATE PROCEDURE Inventario.sp_AsignarEtiqueta
    @ProductoId INT,
    @EtiquetaId INT,
    @UsuarioId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El producto especificado no existe' AS Mensaje;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM Inventario.Etiquetas WHERE Id = @EtiquetaId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La etiqueta especificada no existe' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM Inventario.ProductoEtiqueta WHERE ProductoId = @ProductoId AND EtiquetaId = @EtiquetaId)
        BEGIN
            SELECT CAST(1 AS BIT) AS Exito, 'El producto ya tiene asignada esta etiqueta' AS Mensaje;
            RETURN;
        END

        BEGIN TRAN;

        INSERT INTO Inventario.ProductoEtiqueta (ProductoId, EtiquetaId)
        VALUES (@ProductoId, @EtiquetaId);

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'ASIGNAR_ETIQUETA',
            @TablaAfectada = 'Inventario.ProductoEtiqueta',
            @RegistroId = CAST(@ProductoId AS NVARCHAR(50)) + '-' + CAST(@EtiquetaId AS NVARCHAR(50)),
            @Detalle = 'Etiqueta asignada al producto';

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Etiqueta asignada correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        -- Si dos solicitudes asignan la misma etiqueta casi al mismo tiempo,
        -- la validación de arriba no alcanza a evitar la carrera: tratamos
        -- la violación de PK como el mismo caso "ya estaba asignada" (éxito
        -- idempotente), no como un error real.
        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(1 AS BIT) AS Exito, 'El producto ya tiene asignada esta etiqueta' AS Mensaje;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO