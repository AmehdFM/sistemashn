CREATE PROCEDURE Inventario.sp_CrearCategoria
    @Nombre NVARCHAR(100),
    @CategoriaPadreId INT = NULL,
    @UsuarioId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF @CategoriaPadreId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Inventario.Categorias WHERE Id = @CategoriaPadreId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La categoría padre especificada no existe' AS Mensaje, NULL AS CategoriaId;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM Inventario.Categorias WHERE Nombre = @Nombre AND ((CategoriaPadreId = @CategoriaPadreId) OR (CategoriaPadreId IS NULL AND @CategoriaPadreId IS NULL)))
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe una categoría con el mismo nombre bajo el mismo padre' AS Mensaje, NULL AS CategoriaId;
            RETURN;
        END

        BEGIN TRAN;

        INSERT INTO Inventario.Categorias (Nombre, CategoriaPadreId, Activo)
        VALUES (@Nombre, @CategoriaPadreId, 1);

        DECLARE @CategoriaId INT = SCOPE_IDENTITY();

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'CREAR_CATEGORIA',
            @TablaAfectada = 'Inventario.Categorias',
            @RegistroId = CAST(@CategoriaId AS NVARCHAR(50)),
            @Detalle = 'Categoría creada: ' + @Nombre;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'Categoría creada correctamente' AS Mensaje, @CategoriaId AS CategoriaId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe una categoría con el mismo nombre bajo el mismo padre' AS Mensaje, NULL AS CategoriaId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS CategoriaId;
    END CATCH
END
GO