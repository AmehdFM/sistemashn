-- Defecto C-6: Configuracion.Logo es VARBINARY(MAX) y cada lectura de la
-- configuración general lo arrastra si se hace SELECT *. Con 1 GB de buffer
-- pool, eso no es gratis. Ningún otro SP debe leer esta columna: el logo se
-- consulta únicamente acá, y solo cuando hace falta (al imprimir).
CREATE PROCEDURE Configuracion.sp_ObtenerLogo
AS
BEGIN
    SET NOCOUNT ON;

    SELECT Logo
    FROM Configuracion.Configuracion
    WHERE Id = 1;
END
GO
