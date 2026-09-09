-- Asume la decisión D-3 resuelta como opción (c): no se permite rearmar un
-- paquete que ya tiene ventas registradas (evita que la anulación restaure
-- al inventario una composición distinta a la que realmente salió).
--
CREATE PROCEDURE Repuestos.sp_ArmarPaquete
    @ProductoIdPaquete  INT,
    @UsuarioId          INT,
    @Componentes        Repuestos.PaqueteDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'El producto del paquete no existe: créelo primero como producto' AS Mensaje;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM @Componentes)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El paquete debe tener al menos un componente' AS Mensaje;
            RETURN;
        END

        -- Regla que un CHECK no puede expresar: no se permiten paquetes anidados,
        -- porque un CHECK no puede consultar otra tabla.
        IF EXISTS (SELECT 1 FROM @Componentes c
                   INNER JOIN Repuestos.Paquetes p ON p.ProductoId = c.ComponenteProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'No se permiten paquetes anidados: un componente no puede ser otro paquete' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes WHERE ComponenteProductoId = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El paquete no puede contenerse a sí mismo' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes c
                   INNER JOIN Inventario.Productos p ON p.Id = c.ComponenteProductoId
                   WHERE p.Activo = 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay componentes inactivos en la lista' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes c
                   INNER JOIN Inventario.Productos p ON p.Id = c.ComponenteProductoId
                   INNER JOIN Inventario.UnidadesMedida um ON um.Id = p.UnidadMedidaId
                   WHERE um.PermiteFraccion = 0 AND c.Cantidad <> ROUND(c.Cantidad, 0))
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay componentes cuya unidad de medida no admite cantidades fraccionarias' AS Mensaje;
            RETURN;
        END

        -- Decisión D-3 (c): rearmar un paquete ya vendido rompería la
        -- anulación, porque se devolverían al inventario componentes
        -- distintos a los que salieron.
        IF EXISTS (SELECT 1 FROM Repuestos.Paquetes pq
                   WHERE pq.ProductoId = @ProductoIdPaquete)
           AND EXISTS (SELECT 1 FROM Repuestos.VentaDetalle vd
                       WHERE vd.ProductoId = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'Este paquete ya tiene ventas registradas y no puede modificarse. Cree un paquete nuevo.' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoPaquete;

        IF NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes WHERE ProductoId = @ProductoIdPaquete)
            INSERT INTO Repuestos.Paquetes (ProductoId) VALUES (@ProductoIdPaquete);
        ELSE
            DELETE FROM Repuestos.PaqueteDetalle WHERE PaqueteId = @ProductoIdPaquete;

        -- El TVP puede traer el mismo componente repetido; se agrupa antes de
        -- insertar para que el UNIQUE (PaqueteId, ComponenteProductoId) no
        -- rechace el lote entero (misma clase de defecto que B-4).
        INSERT INTO Repuestos.PaqueteDetalle (PaqueteId, ComponenteProductoId, Cantidad)
        SELECT @ProductoIdPaquete, ComponenteProductoId, SUM(Cantidad)
        FROM @Componentes
        GROUP BY ComponenteProductoId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'PAQUETE_ARMADO',
            @TablaAfectada = 'Repuestos.Paquetes', @RegistroId = @ProductoIdPaquete;

        SELECT CAST(1 AS BIT) AS Exito, 'Paquete armado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPaquete;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
