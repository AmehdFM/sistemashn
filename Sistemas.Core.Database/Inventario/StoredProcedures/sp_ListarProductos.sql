CREATE PROCEDURE Inventario.sp_ListarProductos
    @SoloActivos BIT = 1,
    @CategoriaId INT = NULL,
    @Busqueda NVARCHAR(150) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        p.Id,
        p.Codigo,
        p.Nombre,
        p.Descripcion,
        p.PrecioUnitario,
        p.CategoriaId,
        c.Nombre AS NombreCategoria,
        p.TasaISV,
        p.StockActual,
        p.StockMinimo,
        p.Activo,
        p.FechaCreacion
    FROM Inventario.Productos p
    LEFT JOIN Inventario.Categorias c ON p.CategoriaId = c.Id
    WHERE (@SoloActivos = 0 OR p.Activo = @SoloActivos)
      AND (@CategoriaId IS NULL OR p.CategoriaId = @CategoriaId)
      AND (@Busqueda IS NULL OR p.Codigo LIKE '%' + @Busqueda + '%' OR p.Nombre LIKE '%' + @Busqueda + '%');
END
GO
