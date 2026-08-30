-- ============================================================================
-- Security.sp_ObtenerCredencialesLogin
--
-- Devuelve el hash BCrypt almacenado para un usuario, junto con su información
-- básica, para que la capa C# haga la verificación con BCrypt.Verify().
--
-- IMPORTANTE: este SP NUNCA compara contraseñas. BCrypt genera un salt
-- aleatorio distinto en cada hash, por lo que comparar dos hashes por
-- igualdad en T-SQL es incorrecto — casi nunca coincidirían aunque la
-- contraseña sea correcta. La verificación real ocurre en C# con
-- BCrypt.Net (BCrypt.Verify(passwordPlano, hashDevuelto)).
--
-- Diseñado para on-premise: nunca deja escapar una excepción cruda hacia
-- la app. Cualquier fallo inesperado (timeout, BD no disponible, etc.)
-- se captura y se devuelve como Exito = 0, para que la app pueda manejar
-- un mensaje controlado en vez de una excepción no atrapada.
-- ============================================================================
CREATE PROCEDURE Security.sp_ObtenerCredencialesLogin
    @NombreUsuario NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        DECLARE @UsuarioId INT;
        DECLARE @PasswordHash NVARCHAR(255);
        DECLARE @Activo BIT;
        DECLARE @NombreCompleto NVARCHAR(100);
        DECLARE @RolId INT;
        DECLARE @NombreRol NVARCHAR(50);

        SELECT
            @UsuarioId      = u.Id,
            @PasswordHash   = u.PasswordHash,
            @Activo         = u.Activo,
            @NombreCompleto = u.NombreCompleto,
            @RolId          = u.RolId,
            @NombreRol      = r.Nombre
        FROM Security.Usuarios u
        INNER JOIN Security.Roles r ON u.RolId = r.Id
        WHERE u.NombreUsuario = @NombreUsuario;

        -- Usuario no existe o está desactivado: NO revelamos cuál de las dos
        -- cosas pasó (evita que un atacante use el sistema para enumerar
        -- nombres de usuario válidos).
        IF @UsuarioId IS NULL OR @Activo = 0
        BEGIN
            SELECT
                CAST(0 AS BIT)              AS Exito,
                CAST(NULL AS INT)           AS UsuarioId,
                CAST(NULL AS NVARCHAR(255)) AS PasswordHash,
                CAST(NULL AS NVARCHAR(100)) AS NombreCompleto,
                CAST(NULL AS INT)           AS RolId,
                CAST(NULL AS NVARCHAR(50))  AS NombreRol;
            RETURN;
        END

        SELECT
            CAST(1 AS BIT)   AS Exito,
            @UsuarioId       AS UsuarioId,
            @PasswordHash    AS PasswordHash,
            @NombreCompleto  AS NombreCompleto,
            @RolId           AS RolId,
            @NombreRol       AS NombreRol;
    END TRY
    BEGIN CATCH
        -- Fallo inesperado de SQL Server (no de credenciales). Nunca dejar
        -- que esta excepción llegue cruda a la app.
        SELECT
            CAST(0 AS BIT)              AS Exito,
            CAST(NULL AS INT)           AS UsuarioId,
            CAST(NULL AS NVARCHAR(255)) AS PasswordHash,
            CAST(NULL AS NVARCHAR(100)) AS NombreCompleto,
            CAST(NULL AS INT)           AS RolId,
            CAST(NULL AS NVARCHAR(50))  AS NombreRol;
    END CATCH
END
GO