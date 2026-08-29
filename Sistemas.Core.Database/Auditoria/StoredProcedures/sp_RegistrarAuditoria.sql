CREATE PROCEDURE Auditoria.sp_RegistrarAuditoria
    @UsuarioId INT = NULL,
    @Accion NVARCHAR(50),
    @TablaAfectada NVARCHAR(100) = NULL,
    @RegistroId NVARCHAR(50) = NULL,
    @Detalle NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        INSERT INTO Auditoria.Auditoria (UsuarioId, Accion, TablaAfectada, RegistroId, Detalle, FechaHora)
        VALUES (@UsuarioId, @Accion, @TablaAfectada, @RegistroId, @Detalle, SYSDATETIME());
    END TRY
    BEGIN CATCH
        DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();
        PRINT 'Error registrando auditoría: ' + @ErrMsg;
    END CATCH
END
GO
