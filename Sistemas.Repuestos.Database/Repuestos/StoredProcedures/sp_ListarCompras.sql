-- Historial de compras, paginado. Sin esto no hay forma de ver ni localizar
-- una compra ya registrada (sp_RegistrarCompra solo permite crear).
CREATE PROCEDURE Repuestos.sp_ListarCompras
    @ProveedorId   INT = NULL,
    @Pagina        INT = 1,
    @TamanoPagina  INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @TamanoPagina > 500 SET @TamanoPagina = 500;
    IF @Pagina < 1 SET @Pagina = 1;

    SELECT
        c.Id, c.Fecha, c.ProveedorId, p.Nombre AS NombreProveedor,
        c.NumeroFacturaProveedor, c.Total, c.EsCredito, c.UsuarioId
    FROM Repuestos.Compras c
    INNER JOIN Repuestos.Proveedores p ON p.Id = c.ProveedorId
    WHERE (@ProveedorId IS NULL OR c.ProveedorId = @ProveedorId)
    ORDER BY c.Fecha DESC
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM Repuestos.Compras c
    WHERE (@ProveedorId IS NULL OR c.ProveedorId = @ProveedorId);
END
GO
