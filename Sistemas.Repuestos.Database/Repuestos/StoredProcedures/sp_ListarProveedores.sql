-- Mismo patrón de sp_ListarProductos (Anexo B.7 del plan): paginación
-- obligatoria (sección 6) y OPTION (RECOMPILE) por los parámetros opcionales.
-- Lista los terceros marcados con el rol EsProveedor.
CREATE PROCEDURE Repuestos.sp_ListarProveedores
    @SoloActivos  BIT = 1,
    @Busqueda     NVARCHAR(150) = NULL,
    @Pagina       INT = 1,
    @TamanoPagina INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    SELECT Id, Nombre, Empresa, Correo, Telefono, RTN, EsProveedor, EsCliente, Activo
    FROM Repuestos.Terceros
    WHERE EsProveedor = 1
      AND (@SoloActivos = 0 OR Activo = 1)
      AND (@Busqueda IS NULL OR Nombre LIKE '%' + @Busqueda + '%')
    ORDER BY Nombre
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    SELECT COUNT(*) AS TotalFilas
    FROM Repuestos.Terceros
    WHERE EsProveedor = 1
      AND (@SoloActivos = 0 OR Activo = 1)
      AND (@Busqueda IS NULL OR Nombre LIKE '%' + @Busqueda + '%')
    OPTION (RECOMPILE);
END
GO
