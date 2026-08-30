-- ============================================================================
-- Facturacion.sp_ObtenerCorrelativoCAI
--
-- Obtiene el siguiente correlativo de facturación de forma atómica.
-- UPDLOCK + HOLDLOCK asegura que dos llamadas simultáneas nunca reciban
-- el mismo correlativo (la segunda espera a que la primera confirme).
--
-- Consideraciones on-premise / no debe colgar el sistema:
--   - LOCK_TIMEOUT: si el bloqueo tarda más de 5 segundos, falla de forma
--     controlada en vez de dejar la caja esperando indefinidamente.
--   - XACT_ABORT ON: cualquier error deja la transacción en estado limpio,
--     no solo los casos que el código anticipa explícitamente.
--   - Errores inesperados nunca muestran el mensaje técnico crudo de SQL
--     Server al cajero — se registra en auditoría y se devuelve un mensaje
--     genérico, con un código de referencia para que soporte lo ubique.
-- ============================================================================
CREATE PROCEDURE Facturacion.sp_ObtenerCorrelativoCAI
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000; -- 5 segundos; evita espera indefinida en la caja

    BEGIN TRY
        BEGIN TRAN;

        DECLARE @Id INT, @RangoAutorizado NVARCHAR(40), @CorrelativoActual CHAR(16),
                @RangoFinal CHAR(16), @FechaVencimiento DATE;

        SELECT
            @Id = Id,
            @RangoAutorizado = RangoAutorizado,
            @CorrelativoActual = CorrelativoActual,
            @RangoFinal = RangoFinal,
            @FechaVencimiento = FechaVencimiento
        FROM Facturacion.ConfiguracionCAI WITH (UPDLOCK, HOLDLOCK)
        WHERE Activo = 1;

        IF @Id IS NULL
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'No hay un CAI activo configurado' AS Mensaje, CAST(NULL AS NVARCHAR(60)) AS Correlativo;
            RETURN;
        END

        IF @FechaVencimiento < CAST(SYSDATETIME() AS DATE)
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'El CAI configurado está vencido' AS Mensaje, CAST(NULL AS NVARCHAR(60)) AS Correlativo;
            RETURN;
        END

        IF @CorrelativoActual >= @RangoFinal
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'El rango de CAI se agotó, contactar al administrador' AS Mensaje, CAST(NULL AS NVARCHAR(60)) AS Correlativo;
            RETURN;
        END

        DECLARE @Siguiente CHAR(16) = RIGHT('0000000000000000' + CAST(CAST(@CorrelativoActual AS BIGINT) + 1 AS NVARCHAR(16)), 16);

        UPDATE Facturacion.ConfiguracionCAI
        SET CorrelativoActual = @Siguiente
        WHERE Id = @Id;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'OK' AS Mensaje, @RangoAutorizado + '-' + @Siguiente AS Correlativo;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        DECLARE @ErrorNumero INT = ERROR_NUMBER();
        DECLARE @ErrorMsgTecnico NVARCHAR(2000) = ERROR_MESSAGE();
        DECLARE @RefError NVARCHAR(50) = 'CAI-' + CONVERT(NVARCHAR(30), SYSDATETIME(), 120);

        -- Registrar el detalle técnico en auditoría para que soporte pueda
        -- investigar; nunca se muestra este texto crudo al usuario final.
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = NULL,
            @Accion = 'ERROR_SP',
            @TablaAfectada = 'Facturacion.ConfiguracionCAI',
            @RegistroId = @RefError,
            @Detalle = CONCAT('sp_ObtenerCorrelativoCAI - Error ', @ErrorNumero, ': ', @ErrorMsgTecnico);

        -- 1222 = "Lock request time out period exceeded" -> mensaje específico
        IF @ErrorNumero = 1222
            SELECT CAST(0 AS BIT) AS Exito,
                   'Sistema ocupado procesando otra venta, intente nuevamente' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('Error interno al generar el correlativo. Referencia: ', @RefError) AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
    END CATCH
END
GO