-- Decisión D-1: Auditoria.Auditoria es la única tabla de crecimiento
-- ilimitado y el límite de SQL Server Express es 10 GB para toda la base.
-- Sin purga, el sistema deja de aceptar ventas por una tabla de bitácora.
--
-- Borra en lotes pequeños dentro de un WHILE: un DELETE masivo de una tabla
-- de millones de filas escala el bloqueo a nivel de tabla y congela el
-- sistema completo. En lotes, cada transacción es corta y otras sesiones
-- (la caja) siguen trabajando durante la purga.
--
-- Lo dispara Sistemas.Mantenimiento, no un job del SQL Server Agent:
-- SQL Server Express no incluye Agent.
CREATE PROCEDURE Auditoria.sp_PurgarAuditoria
    @DiasAConservar INT = 365
AS
BEGIN
    SET NOCOUNT ON;

    IF @DiasAConservar < 90 SET @DiasAConservar = 90;   -- piso de seguridad

    DECLARE @Corte DATETIME2(0) = DATEADD(DAY, -@DiasAConservar, SYSDATETIME());
    DECLARE @Borradas INT = 1, @Total INT = 0;

    WHILE @Borradas > 0
    BEGIN
        DELETE TOP (5000) FROM Auditoria.Auditoria WHERE FechaHora < @Corte;
        SET @Borradas = @@ROWCOUNT;
        SET @Total = @Total + @Borradas;

        IF @Borradas > 0 WAITFOR DELAY '00:00:00.100';
    END

    SELECT CAST(1 AS BIT) AS Exito,
           CONCAT('Purga completada: ', @Total, ' registros eliminados') AS Mensaje,
           @Total AS FilasEliminadas;
END
GO
