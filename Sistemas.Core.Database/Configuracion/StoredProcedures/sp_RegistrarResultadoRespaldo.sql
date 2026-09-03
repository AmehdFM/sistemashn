-- Sección 7: Sistemas.Mantenimiento llama esto DESPUÉS de intentar el
-- respaldo diario (BACKUP DATABASE ... WITH COMPRESSION, CHECKSUM) y su
-- verificación (RESTORE VERIFYONLY). Este SP no ejecuta el respaldo, solo
-- registra el resultado — igual que sp_RegistrarResultadoLogin registra el
-- resultado de un login que la app ya validó.
CREATE PROCEDURE Configuracion.sp_RegistrarResultadoRespaldo
    @Exito       BIT,
    @RutaDestino NVARCHAR(260) = NULL,
    @TamanoBytes BIGINT        = NULL,
    @Mensaje     NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO Configuracion.HistorialRespaldos (Exito, RutaDestino, TamanoBytes, Mensaje)
    VALUES (@Exito, @RutaDestino, @TamanoBytes, @Mensaje);

    SELECT CAST(1 AS BIT) AS Exito, 'Resultado de respaldo registrado' AS Mensaje;
END
GO
