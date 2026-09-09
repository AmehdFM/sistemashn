-- No se permite tocar Codigo (clave natural) ni, para la unidad "Unidad"
-- (Id = 1), PermiteFraccion/Activo: es la unidad por defecto de todo
-- producto nuevo y de la validación de enteros en toda la app — cambiarla
-- rompería esa garantía en silencio para productos ya existentes.
CREATE PROCEDURE Inventario.sp_ActualizarUnidadMedida
    @UnidadMedidaId INT,
    @Nombre NVARCHAR(50),
    @Simbolo NVARCHAR(10),
    @PermiteFraccion BIT,
    @Sistema NVARCHAR(20) = NULL,
    @Activo BIT = 1,
    @UsuarioId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Id = @UnidadMedidaId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La unidad de medida especificada no existe' AS Mensaje;
            RETURN;
        END

        IF @UnidadMedidaId = 1 AND (@PermiteFraccion <> 0 OR @Activo = 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La unidad "Unidad" no puede desactivarse ni admitir fracciones' AS Mensaje;
            RETURN;
        END

        BEGIN TRAN;

        UPDATE Inventario.UnidadesMedida
        SET Nombre = @Nombre,
            Simbolo = @Simbolo,
            PermiteFraccion = @PermiteFraccion,
            Sistema = @Sistema,
            Activo = @Activo
        WHERE Id = @UnidadMedidaId;

        COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'ACTUALIZAR_UNIDAD_MEDIDA',
            @TablaAfectada = 'Inventario.UnidadesMedida',
            @RegistroId = @UnidadMedidaId;

        SELECT CAST(1 AS BIT) AS Exito, 'Unidad de medida actualizada correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
