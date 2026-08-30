-- ============================================================================
-- Inventario.sp_ImportarProductosMasivo
--
-- Importa/actualiza productos en lote (típicamente desde Excel).
--
-- IMPORTANTE: procesa fila por fila, cada una en su propia transacción,
-- para cumplir el requisito de que UNA fila con error nunca tumbe el
-- resto del lote. Por eso este SP NO usa SET XACT_ABORT ON a propósito
-- (lo contradiría: abortaría todo el batch en el primer error).
--
-- Devuelve DOS result sets:
--   1) Resumen: Exito, Mensaje, FilasExitosas, FilasFallidas
--   2) Detalle por fila: Codigo, Exito, Mensaje, Accion — para que la app
--      pueda resaltar exactamente qué filas del Excel fallaron y por qué.
--
-- En C#/Dapper, esto se consume con QueryMultipleAsync (dos result sets),
-- no con Execute/QuerySingle.
-- ============================================================================
CREATE PROCEDURE Inventario.sp_ImportarProductosMasivo
    @Productos Inventario.ProductoTableType READONLY,
    @UsuarioId INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Resultados TABLE (
        Codigo  NVARCHAR(30),
        Exito   BIT,
        Mensaje NVARCHAR(300),
        Accion  NVARCHAR(20) NULL -- 'INSERT' o 'UPDATE'; NULL si falló
    );

    DECLARE @Codigo NVARCHAR(30), @Nombre NVARCHAR(150), @Descripcion NVARCHAR(500),
            @PrecioUnitario DECIMAL(12,2), @CategoriaId INT, @TasaISV DECIMAL(5,2), @StockMinimo INT;

    DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
        SELECT Codigo, Nombre, Descripcion, PrecioUnitario, CategoriaId, TasaISV, StockMinimo
        FROM @Productos;

    OPEN cur;
    FETCH NEXT FROM cur INTO @Codigo, @Nombre, @Descripcion, @PrecioUnitario, @CategoriaId, @TasaISV, @StockMinimo;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            -- Validaciones de negocio previas con mensajes claros por fila,
            -- en vez de dejar que el CHECK constraint crudo explique el error
            IF @Codigo IS NULL OR LEN(LTRIM(RTRIM(@Codigo))) = 0
                INSERT INTO @Resultados VALUES (@Codigo, 0, 'Código vacío o nulo', NULL);
            ELSE IF @Nombre IS NULL OR LEN(LTRIM(RTRIM(@Nombre))) = 0
                INSERT INTO @Resultados VALUES (@Codigo, 0, 'Nombre vacío o nulo', NULL);
            ELSE IF @PrecioUnitario IS NULL OR @PrecioUnitario < 0
                INSERT INTO @Resultados VALUES (@Codigo, 0, 'Precio unitario inválido (nulo o negativo)', NULL);
            ELSE IF @TasaISV IS NOT NULL AND @TasaISV NOT IN (0.00, 15.00, 18.00)
                INSERT INTO @Resultados VALUES (@Codigo, 0, 'Tasa de ISV inválida (debe ser 0, 15 o 18)', NULL);
            ELSE IF @CategoriaId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Inventario.Categorias WHERE Id = @CategoriaId)
                INSERT INTO @Resultados VALUES (@Codigo, 0, 'La categoría especificada no existe', NULL);
            ELSE
            BEGIN
                BEGIN TRAN;

                IF EXISTS (SELECT 1 FROM Inventario.Productos WHERE Codigo = @Codigo)
                BEGIN
                    UPDATE Inventario.Productos
                    SET Nombre         = @Nombre,
                        Descripcion    = @Descripcion,
                        PrecioUnitario = @PrecioUnitario,
                        CategoriaId    = @CategoriaId,
                        TasaISV        = ISNULL(@TasaISV, TasaISV),
                        StockMinimo    = ISNULL(@StockMinimo, StockMinimo)
                    WHERE Codigo = @Codigo;

                    INSERT INTO @Resultados VALUES (@Codigo, 1, 'Actualizado', 'UPDATE');
                END
                ELSE
                BEGIN
                    INSERT INTO Inventario.Productos (Codigo, Nombre, Descripcion, PrecioUnitario, CategoriaId, TasaISV, StockMinimo)
                    VALUES (@Codigo, @Nombre, @Descripcion, @PrecioUnitario, @CategoriaId,
                            ISNULL(@TasaISV, 15.00), ISNULL(@StockMinimo, 0));

                    INSERT INTO @Resultados VALUES (@Codigo, 1, 'Creado', 'INSERT');
                END

                COMMIT;
            END
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK;
            -- Contexto de importación admin (no un cajero en medio de una venta):
            -- el mensaje técnico crudo sí es útil aquí para corregir el Excel.
            INSERT INTO @Resultados VALUES (@Codigo, 0, ERROR_MESSAGE(), NULL);
        END CATCH

        FETCH NEXT FROM cur INTO @Codigo, @Nombre, @Descripcion, @PrecioUnitario, @CategoriaId, @TasaISV, @StockMinimo;
    END

    CLOSE cur;
    DEALLOCATE cur;

    DECLARE @TotalExitosos INT = (SELECT COUNT(*) FROM @Resultados WHERE Exito = 1);
    DECLARE @TotalFallidos INT = (SELECT COUNT(*) FROM @Resultados WHERE Exito = 0);

    -- La auditoría del resumen nunca debe impedir que el resultado se devuelva,
    -- aunque falle (ej. problema puntual con Auditoria), por eso va en su propio TRY/CATCH
    BEGIN TRY
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'IMPORTACION_MASIVA_PRODUCTOS',
            @TablaAfectada = 'Inventario.Productos',
            @Detalle = CONCAT('Exitosos: ', @TotalExitosos, ', Fallidos: ', @TotalFallidos);
    END TRY
    BEGIN CATCH
        -- Silenciado intencionalmente: la importación ya se hizo, un fallo
        -- de auditoría aquí no debe impedir devolver el resultado al usuario.
    END CATCH

    -- Result set 1: resumen
    SELECT
        CAST(1 AS BIT) AS Exito,
        CONCAT('Importación completada: ', @TotalExitosos, ' exitosos, ', @TotalFallidos, ' fallidos') AS Mensaje,
        @TotalExitosos AS FilasExitosas,
        @TotalFallidos AS FilasFallidas;

    -- Result set 2: detalle por fila
    SELECT Codigo, Exito, Mensaje, Accion FROM @Resultados;
END
GO