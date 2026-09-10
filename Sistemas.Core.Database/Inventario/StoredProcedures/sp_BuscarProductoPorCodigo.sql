-- Match EXACTO por código interno o código de barras (0 o 1 fila). Existe
-- separado de sp_ListarProductos (que busca por LIKE) porque la regla
-- "código exacto pesa más que búsqueda parcial" vive en que este SP exista
-- y el llamador lo intente primero — no en que C# compare strings.
CREATE PROCEDURE Inventario.sp_BuscarProductoPorCodigo
    @Codigo NVARCHAR(30)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT TOP (1)
        p.Id, p.Codigo, p.CodigoBarra, p.Nombre, p.Descripcion, p.PrecioUnitario,
        p.CategoriaId, c.Nombre AS NombreCategoria,
        p.TasaISV, p.StockActual, p.StockMinimo, p.Activo, p.FechaCreacion
    FROM Inventario.Productos p
    LEFT JOIN Inventario.Categorias c ON p.CategoriaId = c.Id
    WHERE (p.Codigo = @Codigo OR p.CodigoBarra = @Codigo)
      AND p.Activo = 1;
END
GO
