-- Devuelve 0 o 1 fila: la sesión de caja actualmente abierta, si existe.
-- Solo lectura, sin transacción.
CREATE PROCEDURE Repuestos.sp_ObtenerSesionCajaAbierta
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        Id, UsuarioAperturaId, FechaApertura, MontoApertura,
        UsuarioCierreId, FechaCierre, MontoCierreDeclarado, MontoCierreCalculado, Diferencia, Estado
    FROM Repuestos.SesionesCaja
    WHERE Estado = 'Abierta';
END
GO
