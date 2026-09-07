-- Trae el rango CAI activo, para mostrarlo en la pantalla de Facturación.
-- @Existe = 0 significa que todavía no se ha configurado ningún CAI: la
-- pantalla debe mostrarse en blanco (y advertir que el POS no podrá
-- vender), no como un error.
CREATE PROCEDURE Facturacion.sp_ObtenerConfiguracionCAI
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Facturacion.ConfiguracionCAI WHERE Activo = 1)
    BEGIN
        SELECT
            CAST(0 AS BIT)             AS Existe,
            CAST(NULL AS NVARCHAR(40)) AS RangoAutorizado,
            CAST(NULL AS CHAR(16))     AS RangoInicial,
            CAST(NULL AS CHAR(16))     AS RangoFinal,
            CAST(NULL AS CHAR(16))     AS CorrelativoActual,
            CAST(NULL AS DATE)         AS FechaAutorizacion,
            CAST(NULL AS DATE)         AS FechaVencimiento;
        RETURN;
    END

    SELECT
        CAST(1 AS BIT) AS Existe,
        RangoAutorizado, RangoInicial, RangoFinal, CorrelativoActual,
        FechaAutorizacion, FechaVencimiento
    FROM Facturacion.ConfiguracionCAI
    WHERE Activo = 1;
END
GO
