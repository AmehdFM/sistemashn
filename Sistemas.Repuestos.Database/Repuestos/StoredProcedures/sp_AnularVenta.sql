-- Incorpora B-7 (vía D-3 opción c: no se permite rearmar un paquete ya
-- vendido, así que la composición guardada en sp_ArmarPaquete sigue siendo
-- la vigente) y B-8/D-4 (rechazar anular una venta a crédito con pagos ya
-- recibidos, en vez de dejar el estado inconsistente que producía antes).
CREATE PROCEDURE Repuestos.sp_AnularVenta
    @VentaId    INT,
    @UsuarioId  INT,
    @Motivo     NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;
    DECLARE @StockDevuelto TABLE (ProductoId INT PRIMARY KEY, Cantidad INT NOT NULL);

    BEGIN TRY
        IF @Motivo IS NULL OR LEN(LTRIM(RTRIM(@Motivo))) = 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Debe indicar el motivo de la anulación' AS Mensaje;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM Repuestos.Ventas WHERE Id = @VentaId AND Anulada = 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Venta no encontrada o ya estaba anulada' AS Mensaje;
            RETURN;
        END

        -- Decisión D-4: mientras no exista la regla de negocio para devolver
        -- o acreditar el dinero ya recibido, no se permite anular.
        IF EXISTS (SELECT 1
                   FROM Repuestos.CuentasPorCobrar cxc
                   INNER JOIN Repuestos.PagoCuentaPorCobrar p ON p.CuentaPorCobrarId = cxc.Id
                   WHERE cxc.VentaId = @VentaId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'Esta venta a crédito ya tiene pagos registrados y no puede anularse desde el sistema' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoAnulacion;

        -- Misma expansión que en la venta. Es correcta porque D-3 (c) prohíbe
        -- rearmar un paquete que ya tiene ventas: la composición no cambió.
        INSERT INTO @StockDevuelto (ProductoId, Cantidad)
        SELECT ProductoId, SUM(Cantidad)
        FROM (
            SELECT vd.ProductoId, vd.Cantidad
            FROM Repuestos.VentaDetalle vd
            WHERE vd.VentaId = @VentaId
              AND NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes pq WHERE pq.ProductoId = vd.ProductoId)

            UNION ALL

            SELECT pd.ComponenteProductoId, pd.Cantidad * vd.Cantidad
            FROM Repuestos.VentaDetalle vd
            INNER JOIN Repuestos.PaqueteDetalle pd ON pd.PaqueteId = vd.ProductoId
            WHERE vd.VentaId = @VentaId
        ) expandido
        GROUP BY ProductoId;

        UPDATE p
        SET p.StockActual = p.StockActual + sd.Cantidad
        FROM Inventario.Productos p
        INNER JOIN @StockDevuelto sd ON sd.ProductoId = p.Id;

        -- La factura NUNCA se borra: el correlativo CAI ya fue emitido.
        UPDATE Repuestos.Ventas
        SET Anulada = 1, MotivoAnulacion = @Motivo, FechaAnulacion = SYSDATETIME()
        WHERE Id = @VentaId;

        -- Cerrar la cuenta por cobrar si existía y no tenía pagos (defecto B-8)
        UPDATE Repuestos.CuentasPorCobrar
        SET SaldoPendiente = 0, Estado = 'Anulada'
        WHERE VentaId = @VentaId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'VENTA_ANULADA',
            @TablaAfectada = 'Repuestos.Ventas', @RegistroId = @VentaId, @Detalle = @Motivo;

        SELECT CAST(1 AS BIT) AS Exito, 'Venta anulada, stock restaurado' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoAnulacion;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
