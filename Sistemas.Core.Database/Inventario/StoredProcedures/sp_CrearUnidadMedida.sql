CREATE PROCEDURE Inventario.sp_CrearUnidadMedida
    @Codigo NVARCHAR(10),
    @Nombre NVARCHAR(50),
    @Simbolo NVARCHAR(10),
    @PermiteFraccion BIT = 1,
    @Sistema NVARCHAR(20) = NULL,
    @UsuarioId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = @Codigo)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe una unidad de medida con el código especificado' AS Mensaje, NULL AS UnidadMedidaId;
            RETURN;
        END

        BEGIN TRAN;

        INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema, Activo)
        VALUES (@Codigo, @Nombre, @Simbolo, @PermiteFraccion, @Sistema, 1);

        DECLARE @UnidadMedidaId INT = SCOPE_IDENTITY();

        COMMIT;

        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@UnidadMedidaId AS NVARCHAR(50));
        DECLARE @DetalleAuditoria NVARCHAR(500) = 'Unidad de medida creada: ' + @Codigo;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'CREAR_UNIDAD_MEDIDA',
            @TablaAfectada = 'Inventario.UnidadesMedida',
            @RegistroId = @RegistroIdAuditoria,
            @Detalle = @DetalleAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Unidad de medida creada correctamente' AS Mensaje, @UnidadMedidaId AS UnidadMedidaId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe una unidad de medida con el código especificado' AS Mensaje, NULL AS UnidadMedidaId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS UnidadMedidaId;
    END CATCH
END
GO
