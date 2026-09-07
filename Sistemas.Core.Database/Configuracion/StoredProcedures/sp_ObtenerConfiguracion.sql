-- ============================================================================
-- Configuracion.sp_ObtenerConfiguracion
--
-- Trae los datos de Configuracion.Configuracion, incluyendo LogoRuta (la
-- imagen en sí ya no vive en la base de datos — LogoRuta solo apunta a un
-- archivo en Sistemas.Core.Files.FileStorageService, así que es barato
-- traerla en cada lectura, a diferencia del VARBINARY(MAX) que reemplaza).
--
-- @Existe = 0 significa que todavía no se ha guardado ninguna configuración
-- (primer arranque): la pantalla de Ajustes debe mostrarse en blanco, no
-- como un error.
-- ============================================================================
CREATE PROCEDURE Configuracion.sp_ObtenerConfiguracion
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Configuracion.Configuracion WHERE Id = 1)
    BEGIN
        SELECT
            CAST(0 AS BIT)              AS Existe,
            CAST(NULL AS NVARCHAR(150)) AS NombreComercial,
            CAST(NULL AS CHAR(14))      AS RTN,
            CAST(NULL AS NVARCHAR(300)) AS Direccion,
            CAST(NULL AS NVARCHAR(20))  AS Telefono,
            CAST(NULL AS NVARCHAR(100)) AS CorreoContacto,
            CAST(NULL AS NVARCHAR(400)) AS LogoRuta,
            CAST(0 AS BIT)              AS FacturacionLegalActiva,
            CAST(NULL AS DATETIME2(0))  AS FechaActualizacion;
        RETURN;
    END

    SELECT
        CAST(1 AS BIT) AS Existe,
        NombreComercial,
        RTN,
        Direccion,
        Telefono,
        CorreoContacto,
        LogoRuta,
        FacturacionLegalActiva,
        FechaActualizacion
    FROM Configuracion.Configuracion
    WHERE Id = 1;
END
GO
