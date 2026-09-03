CREATE PROCEDURE Inventario.sp_ListarProductos
    @SoloActivos    BIT = 1,
    @CategoriaId    INT = NULL,
    @Busqueda       NVARCHAR(150) = NULL,
    @Pagina         INT = 1,
    @TamanoPagina   INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    -- Nota: @SoloActivos = 0 significa "traer todos", no "solo inactivos".
    -- El nombre del parámetro viene del código original y se conserva por
    -- compatibilidad con la app.

    -- Result set 1: la página
    SELECT
        p.Id, p.Codigo, p.Nombre, p.Descripcion, p.PrecioUnitario,
        p.CategoriaId, c.Nombre AS NombreCategoria,
        p.TasaISV, p.StockActual, p.StockMinimo, p.Activo, p.FechaCreacion
    FROM Inventario.Productos p
    LEFT JOIN Inventario.Categorias c ON p.CategoriaId = c.Id
    WHERE (@SoloActivos = 0 OR p.Activo = 1)
      AND (@CategoriaId IS NULL OR p.CategoriaId = @CategoriaId)
      AND (@Busqueda IS NULL OR p.Codigo LIKE '%' + @Busqueda + '%'
                             OR p.Nombre LIKE '%' + @Busqueda + '%')
    ORDER BY p.Nombre
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    -- Result set 2: total para calcular el número de páginas
    SELECT COUNT(*) AS TotalFilas
    FROM Inventario.Productos p
    WHERE (@SoloActivos = 0 OR p.Activo = 1)
      AND (@CategoriaId IS NULL OR p.CategoriaId = @CategoriaId)
      AND (@Busqueda IS NULL OR p.Codigo LIKE '%' + @Busqueda + '%'
                             OR p.Nombre LIKE '%' + @Busqueda + '%')
    OPTION (RECOMPILE);
END
GO
