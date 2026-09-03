-- Dado un producto, lista sus proveedores ordenados por precio ascendente.
-- Es la consulta que le ahorra dinero al dueño y la razón de existir del
-- módulo de proveedores.
CREATE PROCEDURE Repuestos.sp_CompararPreciosProveedor
    @ProductoId INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        pv.Id AS ProveedorId,
        pv.Nombre,
        pv.Telefono,
        pp.PrecioCompra
    FROM Repuestos.ProductoProveedor pp
    INNER JOIN Repuestos.Proveedores pv ON pv.Id = pp.ProveedorId
    WHERE pp.ProductoId = @ProductoId
      AND pv.Activo = 1
    ORDER BY pp.PrecioCompra ASC;
END
GO
