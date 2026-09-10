-- Historial de sesiones de caja, paginado. Mismo patrón de doble
-- result-set que sp_ListarVentas.
CREATE PROCEDURE Repuestos.sp_ListarSesionesCaja
    @Pagina        INT = 1,
    @TamanoPagina  INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    SELECT
        sc.Id, sc.UsuarioAperturaId, ua.NombreCompleto AS UsuarioAperturaNombre,
        sc.FechaApertura, sc.MontoApertura,
        sc.UsuarioCierreId, uc.NombreCompleto AS UsuarioCierreNombre,
        sc.FechaCierre, sc.MontoCierreDeclarado, sc.MontoCierreCalculado, sc.Diferencia, sc.Estado
    FROM Repuestos.SesionesCaja sc
    INNER JOIN Security.Usuarios ua ON ua.Id = sc.UsuarioAperturaId
    LEFT JOIN Security.Usuarios uc ON uc.Id = sc.UsuarioCierreId
    ORDER BY sc.FechaApertura DESC
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM Repuestos.SesionesCaja sc
    OPTION (RECOMPILE);
END
GO
