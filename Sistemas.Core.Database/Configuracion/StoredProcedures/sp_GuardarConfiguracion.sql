CREATE PROCEDURE Configuracion.sp_GuardarConfiguracion
    @NombreComercial NVARCHAR(150),
    @RTN CHAR(14),
    @Direccion NVARCHAR(300) = NULL,
    @Telefono NVARCHAR(20) = NULL,
    @CorreoContacto NVARCHAR(100) = NULL,
    @Logo VARBINARY(MAX) = NULL,
    @UsuarioId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF LEN(@RTN) <> 14 OR @RTN LIKE '%[^0-9]%'
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El RTN debe tener exactamente 14 dígitos numéricos' AS Mensaje;
            RETURN;
        END

        BEGIN TRAN;

        IF EXISTS (SELECT 1 FROM Configuracion.Configuracion WHERE Id = 1)
        BEGIN
            UPDATE Configuracion.Configuracion
            SET NombreComercial = @NombreComercial,
                RTN = @RTN,
                Direccion = @Direccion,
                Telefono = @Telefono,
                CorreoContacto = @CorreoContacto,
                Logo = @Logo,
                FechaActualizacion = SYSDATETIME()
            WHERE Id = 1;
        END
        ELSE
        BEGIN
            -- Id no es IDENTITY (defecto B-2): se inserta el literal directo,
            -- sin SET IDENTITY_INSERT, que exige permiso ALTER que un usuario
            -- de aplicación con solo EXECUTE no tiene.
            INSERT INTO Configuracion.Configuracion (Id, NombreComercial, RTN, Direccion, Telefono, CorreoContacto, Logo, FechaActualizacion)
            VALUES (1, @NombreComercial, @RTN, @Direccion, @Telefono, @CorreoContacto, @Logo, SYSDATETIME());
        END

        COMMIT;

        -- Auditoría DESPUÉS del commit (defecto B-9): si falla, la configuración
        -- ya quedó guardada y no se pierde por un problema de auditoría.
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'CONFIG_ACTUALIZADA',
            @TablaAfectada = 'Configuracion.Configuracion',
            @RegistroId = '1',
            @Detalle = 'Configuración general actualizada';

        SELECT CAST(1 AS BIT) AS Exito, 'Configuración guardada correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
