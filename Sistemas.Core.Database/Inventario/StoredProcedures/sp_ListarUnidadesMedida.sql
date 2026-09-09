CREATE PROCEDURE Inventario.sp_ListarUnidadesMedida
    @SoloActivas BIT = 1
AS
BEGIN
    SET NOCOUNT ON;

    SELECT Id, Codigo, Nombre, Simbolo, PermiteFraccion, Sistema, Activo
    FROM Inventario.UnidadesMedida
    WHERE (@SoloActivas = 0 OR Activo = 1)
    ORDER BY Nombre;
END
GO
