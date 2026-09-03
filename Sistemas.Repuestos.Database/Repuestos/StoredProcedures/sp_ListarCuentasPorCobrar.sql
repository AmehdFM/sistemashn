-- 'Vencida' no es un estado guardado (se calcularía con un proceso diario
-- que Express no puede correr sin Agent); se calcula al consultar.
CREATE PROCEDURE Repuestos.sp_ListarCuentasPorCobrar
    @SoloConSaldo BIT = 1,
    @Pagina       INT = 1,
    @TamanoPagina INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    SELECT
        cxc.Id, cxc.VentaId, v.NumeroFactura, cxc.MontoOriginal, cxc.SaldoPendiente,
        cxc.FechaVencimiento, cxc.Estado,
        CAST(CASE WHEN cxc.SaldoPendiente > 0 AND cxc.FechaVencimiento < CAST(SYSDATETIME() AS DATE)
                  THEN 1 ELSE 0 END AS BIT) AS EstaVencida
    FROM Repuestos.CuentasPorCobrar cxc
    INNER JOIN Repuestos.Ventas v ON v.Id = cxc.VentaId
    WHERE (@SoloConSaldo = 0 OR cxc.SaldoPendiente > 0)
    ORDER BY cxc.FechaVencimiento
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM Repuestos.CuentasPorCobrar cxc
    WHERE (@SoloConSaldo = 0 OR cxc.SaldoPendiente > 0)
    OPTION (RECOMPILE);
END
GO
