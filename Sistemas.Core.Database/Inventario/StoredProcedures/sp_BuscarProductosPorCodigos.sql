-- Resuelve un lote de códigos distintos en una sola llamada (mismo patrón
-- TVP que VentaDetalleTableType/CompraDetalleTableType) en vez de una
-- consulta por código. Pensado para import de Excel (Compras): el
-- llamador junta los códigos distintos del archivo y los resuelve todos
-- de una vez. Solo lectura, sin transacción.
CREATE PROCEDURE Inventario.sp_BuscarProductosPorCodigos
    @Codigos Inventario.CodigoTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        p.Id, p.Codigo, p.Nombre, p.PrecioUnitario
    FROM Inventario.Productos p
    INNER JOIN @Codigos c ON c.Codigo = p.Codigo
    WHERE p.Activo = 1;
END
GO
