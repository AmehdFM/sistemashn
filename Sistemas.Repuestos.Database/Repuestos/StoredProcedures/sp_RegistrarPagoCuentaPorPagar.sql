-- Idéntico a sp_RegistrarPagoCuentaPorCobrar, sobre Repuestos.CuentasPorPagar.
CREATE PROCEDURE Repuestos.sp_RegistrarPagoCuentaPorPagar
    @CuentaPorPagarId   INT,
    @Monto              DECIMAL(12,2),
    @MetodoPago         NVARCHAR(30) = NULL,
    @UsuarioId          INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000;

    DECLARE @TranPropia BIT = 0;
    DECLARE @SaldoActual DECIMAL(12,2), @Estado NVARCHAR(20);

    BEGIN TRY
        IF @Monto IS NULL OR @Monto <= 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El monto del pago debe ser mayor a cero' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoPago;

        SELECT @SaldoActual = SaldoPendiente, @Estado = Estado
        FROM Repuestos.CuentasPorPagar WITH (UPDLOCK)
        WHERE Id = @CuentaPorPagarId;

        IF @SaldoActual IS NULL
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
            SELECT CAST(0 AS BIT) AS Exito, 'Cuenta por pagar no encontrada' AS Mensaje;
            RETURN;
        END

        IF @Estado = 'Anulada'
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
            SELECT CAST(0 AS BIT) AS Exito, 'La cuenta corresponde a una compra anulada' AS Mensaje;
            RETURN;
        END

        IF @Monto > @SaldoActual
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
            SELECT CAST(0 AS BIT) AS Exito, 'El pago excede el saldo pendiente' AS Mensaje;
            RETURN;
        END

        INSERT INTO Repuestos.PagoCuentaPorPagar (CuentaPorPagarId, Monto, MetodoPago, UsuarioId)
        VALUES (@CuentaPorPagarId, @Monto, @MetodoPago, @UsuarioId);

        UPDATE Repuestos.CuentasPorPagar
        SET SaldoPendiente = SaldoPendiente - @Monto,
            Estado = CASE WHEN SaldoPendiente - @Monto = 0 THEN 'Pagada' ELSE 'PagadaParcial' END
        WHERE Id = @CuentaPorPagarId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'PAGO_CXP_REGISTRADO',
            @TablaAfectada = 'Repuestos.CuentasPorPagar', @RegistroId = @CuentaPorPagarId;

        SELECT CAST(1 AS BIT) AS Exito, 'Pago registrado' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
