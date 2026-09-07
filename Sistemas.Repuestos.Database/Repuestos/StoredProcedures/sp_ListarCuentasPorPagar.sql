-- Idéntico a sp_ListarCuentasPorCobrar, sobre Repuestos.CuentasPorPagar/Compras.
CREATE PROCEDURE Repuestos.sp_ListarCuentasPorPagar
    @SoloConSaldo BIT = 1,
    @ProveedorId  INT = NULL,
    @Pagina       INT = 1,
    @TamanoPagina INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    SELECT
        cxp.Id, cxp.CompraId, c.NumeroFacturaProveedor, cxp.MontoOriginal, cxp.SaldoPendiente,
        cxp.FechaVencimiento, cxp.Estado,
        CAST(CASE WHEN cxp.SaldoPendiente > 0 AND cxp.FechaVencimiento < CAST(SYSDATETIME() AS DATE)
                  THEN 1 ELSE 0 END AS BIT) AS EstaVencida
    FROM Repuestos.CuentasPorPagar cxp
    INNER JOIN Repuestos.Compras c ON c.Id = cxp.CompraId
    WHERE (@SoloConSaldo = 0 OR cxp.SaldoPendiente > 0)
      AND (@ProveedorId IS NULL OR c.ProveedorId = @ProveedorId)
    ORDER BY cxp.FechaVencimiento
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM Repuestos.CuentasPorPagar cxp
    INNER JOIN Repuestos.Compras c ON c.Id = cxp.CompraId
    WHERE (@SoloConSaldo = 0 OR cxp.SaldoPendiente > 0)
      AND (@ProveedorId IS NULL OR c.ProveedorId = @ProveedorId)
    OPTION (RECOMPILE);
END
GO
