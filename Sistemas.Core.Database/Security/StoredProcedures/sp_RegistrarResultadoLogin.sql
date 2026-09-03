-- ============================================================================
-- Security.sp_RegistrarResultadoLogin
--
-- Se llama DESPUÉS de que la app en C# verificó la contraseña con
-- BCrypt.Verify(). Este SP no verifica nada — solo registra el resultado:
-- actualiza UltimoAcceso si fue exitoso, y siempre deja rastro en auditoría.
--
-- Diseñado para on-premise: un fallo al auditar o actualizar UltimoAcceso
-- NUNCA debe impedir que un login válido complete. Por eso el resultado de
-- este SP es informativo (Exito), no bloqueante — la app ya decidió si el
-- login es válido antes de llamar aquí.
-- ============================================================================
CREATE PROCEDURE Security.sp_RegistrarResultadoLogin
    @UsuarioId INT = NULL,
    @NombreUsuarioIntento NVARCHAR(50),
    @Exito BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        IF @Exito = 1 AND @UsuarioId IS NOT NULL
        BEGIN
            UPDATE Security.Usuarios
            SET UltimoAcceso = SYSDATETIME()
            WHERE Id = @UsuarioId;
        END

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = ISNULL(CAST(@UsuarioId AS NVARCHAR(50)), @NombreUsuarioIntento);
        DECLARE @DetalleAuditoria NVARCHAR(500) = CASE WHEN @Exito = 1
                                                        THEN 'Inicio de sesión exitoso'
                                                        ELSE 'Intento de inicio de sesión fallido'
                                                   END;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId      = @UsuarioId,
            @Accion         = 'LOGIN',
            @TablaAfectada  = 'Security.Usuarios',
            @RegistroId     = @RegistroIdAuditoria,
            @Detalle        = @DetalleAuditoria;

        SELECT CAST(1 AS BIT) AS Exito;
    END TRY
    BEGIN CATCH
        -- Un fallo aquí (ej. no se pudo actualizar UltimoAcceso o auditar)
        -- NUNCA debe traducirse en que el usuario no pueda entrar al sistema.
        -- La app ya validó la contraseña antes de llamar este SP; esto es
        -- solo registro. Se devuelve Exito = 0 únicamente para fines de
        -- diagnóstico/telemetría, no para bloquear el flujo de login.
        SELECT CAST(0 AS BIT) AS Exito;
    END CATCH
END
GO