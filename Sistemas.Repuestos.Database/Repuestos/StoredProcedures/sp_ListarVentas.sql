-- Historial de ventas, paginado. Indispensable para el POS: sp_AnularVenta
-- necesita un VentaId, y sin este SP no hay forma de buscarlo por número
-- de factura.
CREATE PROCEDURE Repuestos.sp_ListarVentas
    @NumeroFactura NVARCHAR(60) = NULL,
    @SoloVigentes  BIT = 0,
    @Pagina        INT = 1,
    @TamanoPagina  INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @TamanoPagina > 500 SET @TamanoPagina = 500;
    IF @Pagina < 1 SET @Pagina = 1;

    SELECT
        v.Id, v.NumeroFactura, v.Fecha, v.Subtotal, v.MontoISV, v.Total,
        v.EsCredito, v.Anulada, v.UsuarioId, v.ClienteId, t.Nombre AS ClienteNombre, v.MetodoPago
    FROM Repuestos.Ventas v
    LEFT JOIN Repuestos.Terceros t ON t.Id = v.ClienteId
    WHERE (@NumeroFactura IS NULL OR v.NumeroFactura LIKE '%' + @NumeroFactura + '%')
      AND (@SoloVigentes = 0 OR v.Anulada = 0)
    ORDER BY v.Fecha DESC
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM Repuestos.Ventas v
    WHERE (@NumeroFactura IS NULL OR v.NumeroFactura LIKE '%' + @NumeroFactura + '%')
      AND (@SoloVigentes = 0 OR v.Anulada = 0);
END
GO
