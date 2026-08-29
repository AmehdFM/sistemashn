CREATE PROCEDURE Security.sp_Login
    @NombreUsuario NVARCHAR(50),
    @PasswordHash NVARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @UsuarioId INT;
    DECLARE @NombreCompleto NVARCHAR(100);
    DECLARE @RolId INT;
    DECLARE @NombreRol NVARCHAR(50);
    DECLARE @StoredPasswordHash NVARCHAR(255);
    DECLARE @Activo BIT;

    SELECT 
        @UsuarioId = u.Id,
        @NombreCompleto = u.NombreCompleto,
        @RolId = u.RolId,
        @NombreRol = r.Nombre,
        @StoredPasswordHash = u.PasswordHash,
        @Activo = u.Activo
    FROM Security.Usuarios u
    INNER JOIN Security.Roles r ON u.RolId = r.Id
    WHERE u.NombreUsuario = @NombreUsuario;

    IF @UsuarioId IS NULL OR @Activo = 0 OR @StoredPasswordHash <> @PasswordHash
    BEGIN
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'LOGIN',
            @TablaAfectada = 'Security.Usuarios',
            @RegistroId = @NombreUsuario,
            @Detalle = 'Intento de inicio de sesión fallido';

        SELECT 
            CAST(0 AS BIT) AS Exito, 
            'Usuario o contraseña incorrectos' AS Mensaje,
            NULL AS UsuarioId,
            NULL AS NombreCompleto,
            NULL AS RolId,
            NULL AS NombreRol;
        RETURN;
    END

    UPDATE Security.Usuarios
    SET UltimoAcceso = SYSDATETIME()
    WHERE Id = @UsuarioId;

    EXEC Auditoria.sp_RegistrarAuditoria
        @UsuarioId = @UsuarioId,
        @Accion = 'LOGIN',
        @TablaAfectada = 'Security.Usuarios',
        @RegistroId = CAST(@UsuarioId AS NVARCHAR(50)),
        @Detalle = 'Inicio de sesión exitoso';

    SELECT 
        CAST(1 AS BIT) AS Exito,
        'OK' AS Mensaje,
        @UsuarioId AS UsuarioId,
        @NombreCompleto AS NombreCompleto,
        @RolId AS RolId,
        @NombreRol AS NombreRol;
END
GO
