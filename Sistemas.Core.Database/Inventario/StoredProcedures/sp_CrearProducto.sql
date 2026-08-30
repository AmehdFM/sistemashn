CREATE PROCEDURE Inventario.sp_CrearProducto
    @Codigo NVARCHAR(30),
    @Nombre NVARCHAR(150),
    @Descripcion NVARCHAR(500) = NULL,
    @PrecioUnitario DECIMAL(12,2),
    @CategoriaId INT = NULL,
    @TasaISV DECIMAL(5,2) = 15.00,
    @StockMinimo INT = 0,
    @UsuarioId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF EXISTS (SELECT 1 FROM Inventario.Productos WHERE Codigo = @Codigo)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un producto con el código especificado' AS Mensaje, NULL AS ProductoId;
            RETURN;
        END

        BEGIN TRAN;

        INSERT INTO Inventario.Productos (Codigo, Nombre, Descripcion, PrecioUnitario, CategoriaId, TasaISV, StockActual, StockMinimo, Activo, FechaCreacion)
        VALUES (@Codigo, @Nombre, @Descripcion, @PrecioUnitario, @CategoriaId, @TasaISV, 0, @StockMinimo, 1, SYSDATETIME());

        DECLARE @ProductoId INT = SCOPE_IDENTITY();

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'CREAR_PRODUCTO',
            @TablaAfectada = 'Inventario.Productos',
            @RegistroId = CAST(@ProductoId AS NVARCHAR(50)),
            @Detalle = 'Producto creado: ' + @Codigo;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Producto creado correctamente' AS Mensaje, @ProductoId AS ProductoId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        -- 2627/2601: violación de índice/constraint único. Puede pasar si
        -- dos solicitudes crean el mismo Código casi al mismo tiempo (la
        -- validación de arriba no lo cubre por sí sola, es solo optimización
        -- para el caso común) — se traduce al mismo mensaje amigable.
        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un producto con el código especificado' AS Mensaje, NULL AS ProductoId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS ProductoId;
    END CATCH
END
GO