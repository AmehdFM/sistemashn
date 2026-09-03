-- ============================================================================
-- Facturacion.sp_ObtenerCorrelativoCAI
--
-- Obtiene el siguiente correlativo de facturación de forma atómica.
-- UPDLOCK + HOLDLOCK asegura que dos llamadas simultáneas nunca reciban
-- el mismo correlativo (la segunda espera a que la primera confirme).
--
-- Defecto B-3: este SP puede ser llamado directamente o desde dentro de la
-- transacción de sp_RegistrarVenta. Por eso sigue la plantilla C-5: nunca
-- hace ROLLBACK de una transacción que no abrió. Un ROLLBACK a secas acá
-- revertiría también la venta completa y dejaría al llamador con un
-- ROLLBACK sobre una transacción que ya no existe (error 3903).
--
-- Parámetros OUTPUT (además del result set): SQL Server prohíbe cualquier
-- ROLLBACK dentro de un procedimiento invocado vía INSERT...EXEC. El diseño
-- original de sp_RegistrarVenta capturaba este SP con
-- "INSERT INTO @Resultado EXEC ..." precisamente para leer su result set, lo
-- que rompía el ROLLBACK de las rutas de error (CAI vencido/agotado/ausente)
-- con el error "Cannot use the ROLLBACK statement within an INSERT-EXEC
-- statement." Los OUTPUT permiten a sp_RegistrarVenta llamarlo con un EXEC
-- simple, sin INSERT...EXEC, dejando intacto el ROLLBACK a savepoint. El
-- result set se conserva para quien lo llame directo (ej. Dapper).
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
    @ExitoOut       BIT             = NULL OUTPUT,
    @MensajeOut     NVARCHAR(200)   = NULL OUTPUT,
    @CorrelativoOut NVARCHAR(60)    = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000; -- 5 segundos; evita espera indefinida en la caja

    DECLARE @TranPropia BIT = 0;
    DECLARE @Id INT, @RangoAutorizado NVARCHAR(40), @CorrelativoActual CHAR(16),
            @RangoFinal CHAR(16), @FechaVencimiento DATE, @Siguiente CHAR(16);

    BEGIN TRY
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCAI;

        -- UPDLOCK + HOLDLOCK: dos cajas simultáneas nunca leen el mismo correlativo.
        -- La segunda espera a que la primera confirme y lee el valor ya avanzado.
        SELECT
            @Id                = Id,
            @RangoAutorizado   = RangoAutorizado,
            @CorrelativoActual = CorrelativoActual,
            @RangoFinal        = RangoFinal,
            @FechaVencimiento  = FechaVencimiento
        FROM Facturacion.ConfiguracionCAI WITH (UPDLOCK, HOLDLOCK)
        WHERE Activo = 1;

        IF @Id IS NULL
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
            SET @ExitoOut = 0; SET @MensajeOut = 'No hay un CAI activo configurado'; SET @CorrelativoOut = NULL;
            SELECT @ExitoOut AS Exito, @MensajeOut AS Mensaje, @CorrelativoOut AS Correlativo;
            RETURN;
        END

        IF @FechaVencimiento < CAST(SYSDATETIME() AS DATE)
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
            SET @ExitoOut = 0; SET @MensajeOut = 'El CAI configurado está vencido'; SET @CorrelativoOut = NULL;
            SELECT @ExitoOut AS Exito, @MensajeOut AS Mensaje, @CorrelativoOut AS Correlativo;
            RETURN;
        END

        IF @CorrelativoActual >= @RangoFinal
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
            SET @ExitoOut = 0; SET @MensajeOut = 'El rango de CAI se agotó, contactar al administrador'; SET @CorrelativoOut = NULL;
            SELECT @ExitoOut AS Exito, @MensajeOut AS Mensaje, @CorrelativoOut AS Correlativo;
            RETURN;
        END

        SET @Siguiente = RIGHT('0000000000000000'
                             + CAST(CAST(@CorrelativoActual AS BIGINT) + 1 AS NVARCHAR(16)), 16);

        UPDATE Facturacion.ConfiguracionCAI
        SET CorrelativoActual = @Siguiente
        WHERE Id = @Id;

        IF @TranPropia = 1 COMMIT;

        SET @ExitoOut = 1; SET @MensajeOut = 'OK'; SET @CorrelativoOut = @RangoAutorizado + '-' + @Siguiente;
        SELECT @ExitoOut AS Exito, @MensajeOut AS Mensaje, @CorrelativoOut AS Correlativo;
    END TRY
    BEGIN CATCH
        DECLARE @ErrorNumero     INT            = ERROR_NUMBER();
        DECLARE @ErrorMsgTecnico NVARCHAR(2000) = ERROR_MESSAGE();
        DECLARE @RefError        NVARCHAR(50)   = 'CAI-' + CONVERT(NVARCHAR(30), SYSDATETIME(), 120);

        IF XACT_STATE() = -1
            ROLLBACK;                                   -- condenada: no queda otra
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK;
            ELSE ROLLBACK TRANSACTION PuntoCAI;          -- devuelve solo lo mío, la externa sigue viva
        END

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @DetalleAuditoria NVARCHAR(2000) = CONCAT('sp_ObtenerCorrelativoCAI - Error ', @ErrorNumero, ': ', @ErrorMsgTecnico);

        -- Se audita DESPUÉS de deshacer, nunca dentro de la transacción (defecto B-9)
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = NULL,
            @Accion        = 'ERROR_SP',
            @TablaAfectada = 'Facturacion.ConfiguracionCAI',
            @RegistroId    = @RefError,
            @Detalle       = @DetalleAuditoria;

        -- 1222 = "Lock request time out period exceeded" -> mensaje específico
        IF @ErrorNumero = 1222
        BEGIN
            SET @ExitoOut = 0; SET @MensajeOut = 'Sistema ocupado procesando otra venta, intente nuevamente'; SET @CorrelativoOut = NULL;
        END
        ELSE
        BEGIN
            SET @ExitoOut = 0; SET @MensajeOut = CONCAT('Error interno al generar el correlativo. Referencia: ', @RefError); SET @CorrelativoOut = NULL;
        END

        SELECT @ExitoOut AS Exito, @MensajeOut AS Mensaje, @CorrelativoOut AS Correlativo;
    END CATCH
END
GO
