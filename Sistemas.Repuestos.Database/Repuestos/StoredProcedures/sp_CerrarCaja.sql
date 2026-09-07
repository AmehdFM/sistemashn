-- Cierra la sesión de caja indicada. El monto esperado en la gaveta es
-- siempre la misma cuenta que sp_ObtenerMontoEsperadoCaja: MontoApertura +
-- SUM(Ventas.Total en efectivo, no anuladas, de esta sesión). Se recalcula
-- acá y no se recibe como parámetro para que nunca dependa de lo que haya
-- mostrado la pantalla.
CREATE PROCEDURE Repuestos.sp_CerrarCaja
    @SesionCajaId           INT,
    @UsuarioId              INT,
    @MontoCierreDeclarado   DECIMAL(12,2)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;
    DECLARE @MontoApertura DECIMAL(12,2), @MontoCierreCalculado DECIMAL(12,2), @Diferencia DECIMAL(12,2);

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Repuestos.SesionesCaja WHERE Id = @SesionCajaId AND Estado = 'Abierta')
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La sesión de caja no existe o ya está cerrada' AS Mensaje,
                   CAST(NULL AS DECIMAL(12,2)) AS MontoCierreCalculado, CAST(NULL AS DECIMAL(12,2)) AS Diferencia;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCerrarCaja;

        -- Re-leer con UPDLOCK dentro de la transacción: misma razón que
        -- sp_RegistrarVenta re-valida el stock antes de escribir.
        SELECT @MontoApertura = MontoApertura
        FROM Repuestos.SesionesCaja WITH (UPDLOCK)
        WHERE Id = @SesionCajaId AND Estado = 'Abierta';

        IF @MontoApertura IS NULL
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCerrarCaja;
            SELECT CAST(0 AS BIT) AS Exito, 'La sesión de caja no existe o ya está cerrada' AS Mensaje,
                   CAST(NULL AS DECIMAL(12,2)) AS MontoCierreCalculado, CAST(NULL AS DECIMAL(12,2)) AS Diferencia;
            RETURN;
        END

        SET @MontoCierreCalculado = @MontoApertura + ISNULL((
            SELECT SUM(v.Total)
            FROM Repuestos.Ventas v
            WHERE v.SesionCajaId = @SesionCajaId AND v.MetodoPago = 'Efectivo' AND v.Anulada = 0
        ), 0);

        SET @Diferencia = @MontoCierreDeclarado - @MontoCierreCalculado;

        UPDATE Repuestos.SesionesCaja
        SET Estado = 'Cerrada',
            UsuarioCierreId = @UsuarioId,
            FechaCierre = SYSDATETIME(),
            MontoCierreDeclarado = @MontoCierreDeclarado,
            MontoCierreCalculado = @MontoCierreCalculado,
            Diferencia = @Diferencia
        WHERE Id = @SesionCajaId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'CAJA_CERRADA',
            @TablaAfectada = 'Repuestos.SesionesCaja', @RegistroId = @SesionCajaId;

        SELECT CAST(1 AS BIT) AS Exito, 'Caja cerrada correctamente' AS Mensaje,
               @MontoCierreCalculado AS MontoCierreCalculado, @Diferencia AS Diferencia;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCerrarCaja;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje,
               CAST(NULL AS DECIMAL(12,2)) AS MontoCierreCalculado, CAST(NULL AS DECIMAL(12,2)) AS Diferencia;
    END CATCH
END
GO
