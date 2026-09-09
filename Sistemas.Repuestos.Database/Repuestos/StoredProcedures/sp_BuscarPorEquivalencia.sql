-- Recibe un número (OEM o de parte propio) y devuelve los productos que lo
-- listan como equivalente O cuyo NumeroParte coincide, unificados y
-- paginados. Es la búsqueda central del rubro: "el cliente trae un número
-- de otro fabricante, ¿qué tengo que sirva?".
--
-- Coincidencia exacta (=), no LIKE: es un número de parte, no texto libre,
-- y el índice dedicado sobre NumeroOEM/NumeroParte solo sirve a coincidencia
-- exacta (defecto C-1: un LIKE con comodín inicial no usa índice).
CREATE PROCEDURE Repuestos.sp_BuscarPorEquivalencia
    @Numero       NVARCHAR(50),
    @Pagina       INT = 1,
    @TamanoPagina INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    ;WITH Coincidencias AS (
        SELECT ProductoId, NumeroOEM AS NumeroCoincidente, 'Equivalencia' AS Origen
        FROM Repuestos.NumeroEquivalente
        WHERE NumeroOEM = @Numero

        UNION

        SELECT ProductoId, NumeroParte AS NumeroCoincidente, 'NumeroParte' AS Origen
        FROM Repuestos.DetalleProducto
        WHERE NumeroParte = @Numero
    )
    SELECT
        p.Id, p.Codigo, p.Nombre, p.PrecioUnitario, p.TasaISV, p.StockActual, p.Activo,
        um.Simbolo AS UnidadMedidaSimbolo, um.PermiteFraccion AS PermiteFraccionUnidad,
        c.NumeroCoincidente, c.Origen
    FROM Coincidencias c
    INNER JOIN Inventario.Productos p ON p.Id = c.ProductoId
    LEFT JOIN Inventario.UnidadesMedida um ON um.Id = p.UnidadMedidaId
    ORDER BY p.Nombre
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM (
        SELECT ProductoId FROM Repuestos.NumeroEquivalente WHERE NumeroOEM = @Numero
        UNION
        SELECT ProductoId FROM Repuestos.DetalleProducto WHERE NumeroParte = @Numero
    ) t
    OPTION (RECOMPILE);
END
GO
