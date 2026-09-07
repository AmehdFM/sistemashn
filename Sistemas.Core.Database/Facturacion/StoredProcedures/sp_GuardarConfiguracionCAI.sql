-- Registra un nuevo rango CAI. Un CAI no se "edita": el SAR emite rangos
-- fijos (RangoInicial/RangoFinal ya asignados) que se reemplazan cuando el
-- anterior se agota o vence, nunca se modifican in situ. Por eso este SP
-- desactiva el CAI activo actual (si existe) e inserta uno nuevo, en vez de
-- hacer un UPDATE sobre el existente.
CREATE PROCEDURE Facturacion.sp_GuardarConfiguracionCAI
    @RangoAutorizado   NVARCHAR(40),
    @RangoInicial      CHAR(16),
    @RangoFinal        CHAR(16),
    @FechaAutorizacion DATE,
    @FechaVencimiento  DATE,
    @UsuarioId         INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF @RangoFinal <= @RangoInicial
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El rango final debe ser mayor que el inicial' AS Mensaje;
            RETURN;
        END

        IF @FechaVencimiento <= @FechaAutorizacion
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La fecha de vencimiento debe ser posterior a la de autorización' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCAI;

        -- El índice único filtrado UX_ConfiguracionCAI_UnicoActivo garantiza
        -- que nunca queden dos CAI activos aunque este UPDATE fallara a mitad.
        UPDATE Facturacion.ConfiguracionCAI SET Activo = 0 WHERE Activo = 1;

        INSERT INTO Facturacion.ConfiguracionCAI
            (RangoAutorizado, RangoInicial, RangoFinal, CorrelativoActual, FechaAutorizacion, FechaVencimiento, Activo)
        VALUES
            (@RangoAutorizado, @RangoInicial, @RangoFinal, @RangoInicial, @FechaAutorizacion, @FechaVencimiento, 1);

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'CAI_REGISTRADO',
            @TablaAfectada = 'Facturacion.ConfiguracionCAI',
            @Detalle       = @RangoAutorizado;

        SELECT CAST(1 AS BIT) AS Exito, 'CAI registrado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
