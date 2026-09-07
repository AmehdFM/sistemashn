-- El SP más delicado del sistema. Incorpora las correcciones del plan:
--   B-3: sp_ObtenerCorrelativoCAI ya no destruye esta transacción.
--   B-5: el stock se re-valida CON BLOQUEO dentro de la transacción,
--        porque el chequeo previo (fuera de transacción) es una condición
--        de carrera entre dos cajas.
--   B-6: se valida que todos los productos existan y estén activos ANTES
--        de abrir la transacción.
--
CREATE PROCEDURE Repuestos.sp_RegistrarVenta
    @UsuarioId      INT,
    @ClienteId      INT = NULL,
    @EsCredito      BIT = 0,
    @DiasCredito    INT = NULL,
    @Detalle        Repuestos.VentaDetalleTableType READONLY,
    @MetodoPago       NVARCHAR(20) = 'Efectivo',
    @EfectivoRecibido DECIMAL(12,2) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000;

    DECLARE @TranPropia BIT = 0;
    DECLARE @VentaId INT, @Subtotal DECIMAL(12,2), @MontoISV DECIMAL(12,2), @Total DECIMAL(12,2);
    DECLARE @Correlativo NVARCHAR(60), @MensajeCAI NVARCHAR(200), @ExitoCAI BIT;
    DECLARE @CodigoProblema NVARCHAR(30);
    DECLARE @FacturacionLegalActiva BIT;
    DECLARE @SesionCajaId INT;
    DECLARE @Vuelto DECIMAL(12,2);

    DECLARE @StockRequerido TABLE (ProductoId INT PRIMARY KEY, CantidadRequerida INT NOT NULL);

    BEGIN TRY
        ---------- 1. Validaciones previas, fuera de transacción ----------
        IF NOT EXISTS (SELECT 1 FROM @Detalle)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La venta debe tener al menos un producto' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Detalle WHERE Cantidad <= 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay líneas con cantidad menor o igual a cero' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        IF @EsCredito = 1 AND @ClienteId IS NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Seleccione un cliente para venta a crédito' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        IF @ClienteId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Id = @ClienteId AND EsCliente = 1)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El cliente especificado no existe o no tiene rol de cliente' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        -- Una venta al contado necesita una sesión de caja abierta para que
        -- el historial de caja cuadre siempre contra ventas reales; una
        -- venta a crédito no mueve efectivo todavía y no la necesita.
        IF @EsCredito = 0
        BEGIN
            SELECT TOP (1) @SesionCajaId = Id FROM Repuestos.SesionesCaja WHERE Estado = 'Abierta';

            IF @SesionCajaId IS NULL
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'Abra la caja antes de cobrar' AS Mensaje,
                       CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                       CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
                RETURN;
            END
        END

        -- Defecto B-6: producto inexistente o descontinuado
        IF EXISTS (SELECT 1 FROM @Detalle d
                   WHERE NOT EXISTS (SELECT 1 FROM Inventario.Productos p WHERE p.Id = d.ProductoId))
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay productos en la venta que no existen' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        SELECT TOP (1) @CodigoProblema = p.Codigo
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId
        WHERE p.Activo = 0;

        IF @CodigoProblema IS NOT NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('El producto ', @CodigoProblema, ' está descontinuado y no puede venderse') AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        ---------- 2. Expandir paquetes a componentes reales ----------
        -- Lo que se factura es la línea comercial (el paquete);
        -- lo que se descuenta del inventario son sus componentes.
        INSERT INTO @StockRequerido (ProductoId, CantidadRequerida)
        SELECT ProductoId, SUM(CantidadRequerida)
        FROM (
            SELECT d.ProductoId, d.Cantidad AS CantidadRequerida
            FROM @Detalle d
            WHERE NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes pq WHERE pq.ProductoId = d.ProductoId)

            UNION ALL

            SELECT pd.ComponenteProductoId, pd.Cantidad * d.Cantidad
            FROM @Detalle d
            INNER JOIN Repuestos.PaqueteDetalle pd ON pd.PaqueteId = d.ProductoId
        ) expandido
        GROUP BY ProductoId;   -- un mismo componente puede venir de dos paquetes distintos

        ---------- 3. Chequeo previo de stock (filtro rápido, sin bloquear) ----------
        -- No es la validación definitiva: sirve para no gastar un correlativo
        -- CAI en una venta que ya se sabe condenada.
        IF EXISTS (SELECT 1 FROM @StockRequerido sr
                   INNER JOIN Inventario.Productos p ON p.Id = sr.ProductoId
                   WHERE p.StockActual < sr.CantidadRequerida)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Stock insuficiente para completar la venta' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        ---------- 3.5 Montos y validación de efectivo, TODAVÍA fuera de transacción ----------
        -- Se factura el paquete a su propio precio, no la suma de sus componentes.
        SELECT
            @Subtotal = SUM(d.Cantidad * p.PrecioUnitario),
            @MontoISV = SUM(Facturacion.fn_CalcularISV(d.Cantidad * p.PrecioUnitario, p.TasaISV))
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId;

        SET @Total = @Subtotal + @MontoISV;

        -- El vuelto SIEMPRE lo calcula el servidor con el @Total que él
        -- mismo determinó, nunca el número que mostró el formulario: si el
        -- efectivo declarado no alcanza, la venta se rechaza acá, sin abrir
        -- transacción ni gastar un correlativo CAI.
        IF @MetodoPago = 'Efectivo' AND @EsCredito = 0
        BEGIN
            IF @EfectivoRecibido IS NULL OR @EfectivoRecibido < @Total
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'El efectivo recibido es menor al total de la venta' AS Mensaje,
                       CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                       CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
                RETURN;
            END
            SET @Vuelto = @EfectivoRecibido - @Total;
        END

        ---------- 4. Transacción ----------
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoVenta;

        -- Defecto B-5: re-validar CON BLOQUEO. Sin esto, dos cajas simultáneas
        -- pasan ambas el chequeo del paso 3 y la segunda choca contra el
        -- CHECK (StockActual >= 0) con un error críptico.
        IF EXISTS (SELECT 1 FROM @StockRequerido sr
                   INNER JOIN Inventario.Productos p WITH (UPDLOCK) ON p.Id = sr.ProductoId
                   WHERE p.StockActual < sr.CantidadRequerida)
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVenta;
            SELECT CAST(0 AS BIT) AS Exito,
                   'Stock insuficiente: otra caja vendió el mismo producto' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
            RETURN;
        END

        ---------- 5. Número de factura: CAI (Core) o numeración interna ----------
        -- La facturación legal (CAI) es opcional a nivel de negocio: hay
        -- clientes que aún se están formalizando y no tienen uno vigente.
        -- Cuando está apagada, la venta usa su propia numeración secuencial
        -- en vez de exigir un CAI activo.
        SELECT @FacturacionLegalActiva = FacturacionLegalActiva
        FROM Configuracion.Configuracion WHERE Id = 1;

        IF ISNULL(@FacturacionLegalActiva, 0) = 1
        BEGIN
            -- EXEC simple con OUTPUT, no INSERT...EXEC: SQL Server prohíbe
            -- cualquier ROLLBACK dentro de un procedimiento invocado vía
            -- INSERT...EXEC, y sp_ObtenerCorrelativoCAI necesita poder hacer
            -- ROLLBACK TRANSACTION a su savepoint en sus rutas de error
            -- (CAI vencido/agotado/ausente).
            EXEC Facturacion.sp_ObtenerCorrelativoCAI
                @ExitoOut       = @ExitoCAI OUTPUT,
                @MensajeOut     = @MensajeCAI OUTPUT,
                @CorrelativoOut = @Correlativo OUTPUT;

            IF @ExitoCAI = 0
            BEGIN
                IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVenta;
                SELECT CAST(0 AS BIT) AS Exito, @MensajeCAI AS Mensaje,
                       CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
                   CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
                RETURN;
            END
        END
        ELSE
        BEGIN
            SET @Correlativo = 'INT-' + RIGHT('00000000' + CAST(NEXT VALUE FOR Repuestos.SeqVentaInterna AS NVARCHAR(20)), 8);
        END

        ---------- 6. Persistir la venta con los montos ya calculados ----------
        INSERT INTO Repuestos.Ventas (NumeroFactura, Subtotal, MontoISV, Total, UsuarioId, ClienteId, EsCredito, SesionCajaId, MetodoPago, EfectivoRecibido, Vuelto)
        VALUES (@Correlativo, @Subtotal, @MontoISV, @Total, @UsuarioId, @ClienteId, @EsCredito, @SesionCajaId, @MetodoPago, @EfectivoRecibido, @Vuelto);

        SET @VentaId = SCOPE_IDENTITY();

        -- Precio y tasa se CONGELAN acá: una factura vieja nunca cambia de
        -- valor porque el producto haya cambiado de precio o de tasa después.
        INSERT INTO Repuestos.VentaDetalle (VentaId, ProductoId, Cantidad, PrecioUnitario, TasaISV)
        SELECT @VentaId, d.ProductoId, d.Cantidad, p.PrecioUnitario, p.TasaISV
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId;

        IF @EsCredito = 1
        BEGIN
            INSERT INTO Repuestos.CuentasPorCobrar (VentaId, MontoOriginal, SaldoPendiente, FechaVencimiento)
            VALUES (@VentaId, @Total, @Total,
                    DATEADD(DAY, ISNULL(@DiasCredito, 15), CAST(SYSDATETIME() AS DATE)));
        END

        ---------- 7. Descontar stock (una sola sentencia) ----------
        UPDATE p
        SET p.StockActual = p.StockActual - sr.CantidadRequerida
        FROM Inventario.Productos p
        INNER JOIN @StockRequerido sr ON sr.ProductoId = p.Id;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'VENTA_REGISTRADA',
            @TablaAfectada = 'Repuestos.Ventas', @RegistroId = @VentaId, @Detalle = @Correlativo;

        SELECT CAST(1 AS BIT) AS Exito, 'Venta registrada' AS Mensaje,
               @Correlativo AS NumeroFactura, @Total AS Total,
               @EfectivoRecibido AS EfectivoRecibido, @Vuelto AS Vuelto;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVenta;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje,
               CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total,
               CAST(NULL AS DECIMAL(12,2)) AS EfectivoRecibido, CAST(NULL AS DECIMAL(12,2)) AS Vuelto;
    END CATCH
END
GO
