-- Devuelve TRES result sets en una sola llamada — datos base con
-- LEFT JOIN a DetalleProducto, vehículos compatibles, números equivalentes —
-- que Dapper consume con QueryMultipleAsync. Un viaje a la base en vez de
-- tres: en red local con una PC modesta, el costo dominante es la latencia
-- por llamada, no el volumen.
CREATE PROCEDURE Repuestos.sp_ObtenerProductoRepuesto
    @ProductoId INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Result set 1: datos base + detalle de repuesto (LEFT JOIN: es opcional)
    SELECT
        p.Id, p.Codigo, p.Nombre, p.Descripcion, p.PrecioUnitario,
        p.CategoriaId, p.TasaISV, p.StockActual, p.StockMinimo, p.Activo,
        dp.NumeroParte, dp.MarcaFabricante, dp.EsOriginal
    FROM Inventario.Productos p
    LEFT JOIN Repuestos.DetalleProducto dp ON dp.ProductoId = p.Id
    WHERE p.Id = @ProductoId;

    -- Result set 2: vehículos compatibles
    SELECT Marca, Modelo, AnioDesde, AnioHasta
    FROM Repuestos.VehiculoCompatible
    WHERE ProductoId = @ProductoId
    ORDER BY Marca, Modelo, AnioDesde;

    -- Result set 3: números equivalentes
    SELECT NumeroOEM, Fabricante
    FROM Repuestos.NumeroEquivalente
    WHERE ProductoId = @ProductoId
    ORDER BY Fabricante, NumeroOEM;
END
GO
