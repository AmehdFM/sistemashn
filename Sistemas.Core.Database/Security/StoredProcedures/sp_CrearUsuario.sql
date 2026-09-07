-- ============================================================================
-- Security.sp_CrearUsuario
--
-- Crea un nuevo usuario. @PasswordHash ya viene calculado desde C#
-- (BCrypt.HashPassword) — este SP NUNCA hashea ni compara contraseñas, solo
-- inserta el hash recibido.
--
-- @UsuarioCreadorId es NULL en el asistente de primer usuario (todavía no
-- hay nadie logueado); en cualquier otro caso es el Id del administrador
-- que está dando de alta al nuevo usuario.
-- ============================================================================
CREATE PROCEDURE Security.sp_CrearUsuario
    @NombreUsuario    NVARCHAR(50),
    @PasswordHash     NVARCHAR(255),
    @NombreCompleto   NVARCHAR(100),
    @RolId            INT,
    @UsuarioCreadorId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;
    DECLARE @NuevoUsuarioId INT;

    BEGIN TRY
        IF LEN(LTRIM(RTRIM(ISNULL(@NombreUsuario, '')))) < 3
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El nombre de usuario debe tener al menos 3 caracteres' AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
            RETURN;
        END

        IF LEN(ISNULL(@PasswordHash, '')) = 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La contraseña es requerida' AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
            RETURN;
        END

        IF LEN(LTRIM(RTRIM(ISNULL(@NombreCompleto, '')))) = 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El nombre completo es requerido' AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM Security.Roles WHERE Id = @RolId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El rol especificado no existe' AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM Security.Usuarios WHERE NombreUsuario = @NombreUsuario)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un usuario con ese nombre' AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCrearUsuario;

        INSERT INTO Security.Usuarios (NombreUsuario, PasswordHash, NombreCompleto, RolId, Activo, FechaCreacion)
        VALUES (@NombreUsuario, @PasswordHash, @NombreCompleto, @RolId, 1, SYSDATETIME());

        SET @NuevoUsuarioId = CAST(SCOPE_IDENTITY() AS INT);

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@NuevoUsuarioId AS NVARCHAR(50));
        DECLARE @DetalleAuditoria NVARCHAR(500) = 'Usuario creado: ' + @NombreUsuario;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioCreadorId,
            @Accion        = 'CREAR_USUARIO',
            @TablaAfectada = 'Security.Usuarios',
            @RegistroId    = @RegistroIdAuditoria,
            @Detalle       = @DetalleAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Usuario creado correctamente' AS Mensaje, @NuevoUsuarioId AS UsuarioId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCrearUsuario;
        END

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un usuario con ese nombre' AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS UsuarioId;
    END CATCH
END
GO
