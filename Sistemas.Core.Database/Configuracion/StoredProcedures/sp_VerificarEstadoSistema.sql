-- Sección 7: la app lo consulta al arrancar, ANTES de abrir la caja, para
-- que el dueño se entere de un problema —semanas sin respaldo, CAI por
-- vencerse o por agotarse— antes de necesitarlo, no después.
--
-- Devuelve DOS result sets:
--   1) Una fila por vertical instalada, con su versión de esquema vigente
--      (la de FechaAplicacion más reciente).
--   2) Una sola fila con el estado de respaldo y del CAI activo.
CREATE PROCEDURE Configuracion.sp_VerificarEstadoSistema
    @DiasAvisoVencimientoCAI      INT = 30,   -- avisar si el CAI vence en <= N días
    @CorrelativosAvisoAgotamiento INT = 100   -- avisar si quedan <= N correlativos
AS
BEGIN
    SET NOCOUNT ON;

    -- Result set 1: versión de esquema vigente por vertical
    SELECT
        v.Vertical,
        v.Version,
        v.FechaAplicacion
    FROM Configuracion.VersionEsquema v
    INNER JOIN (
        SELECT Vertical, MAX(FechaAplicacion) AS UltimaFecha
        FROM Configuracion.VersionEsquema
        GROUP BY Vertical
    ) ultima ON ultima.Vertical = v.Vertical AND ultima.UltimaFecha = v.FechaAplicacion;

    -- Result set 2: respaldo y CAI. El LEFT JOIN sobre una fila constante
    -- garantiza exactamente una fila de salida aunque no haya ningún
    -- respaldo registrado todavía o no haya un CAI activo configurado —
    -- ambos son estados reales que la app debe poder mostrar, no un error.
    DECLARE @FechaUltimoRespaldoExitoso DATETIME2(0);
    SELECT @FechaUltimoRespaldoExitoso = MAX(FechaRespaldo)
    FROM Configuracion.HistorialRespaldos
    WHERE Exito = 1;

    SELECT
        @FechaUltimoRespaldoExitoso AS FechaUltimoRespaldoExitoso,
        DATEDIFF(DAY, @FechaUltimoRespaldoExitoso, SYSDATETIME()) AS DiasDesdeUltimoRespaldo,
        cai.RangoAutorizado,
        cai.FechaVencimiento AS FechaVencimientoCAI,
        DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), cai.FechaVencimiento) AS DiasParaVencerCAI,
        CASE WHEN cai.Id IS NULL THEN NULL
             ELSE CAST(cai.RangoFinal AS BIGINT) - CAST(cai.CorrelativoActual AS BIGINT) END AS CorrelativosRestantes,
        CAST(CASE WHEN cai.Id IS NOT NULL
                       AND DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), cai.FechaVencimiento) <= @DiasAvisoVencimientoCAI
                  THEN 1 ELSE 0 END AS BIT) AS CAIProximoAVencer,
        CAST(CASE WHEN cai.Id IS NOT NULL
                       AND (CAST(cai.RangoFinal AS BIGINT) - CAST(cai.CorrelativoActual AS BIGINT)) <= @CorrelativosAvisoAgotamiento
                  THEN 1 ELSE 0 END AS BIT) AS CAIProximoAAgotarse
    FROM (SELECT NULL AS Dummy) base
    LEFT JOIN Facturacion.ConfiguracionCAI cai ON cai.Activo = 1;
END
GO
