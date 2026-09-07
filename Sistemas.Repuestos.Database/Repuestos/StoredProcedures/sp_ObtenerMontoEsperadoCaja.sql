-- Monto que debería haber en la gaveta para la sesión indicada, de solo
-- lectura (sin transacción) — misma fórmula que usa sp_CerrarCaja, para que
-- FormCerrarCaja pueda mostrarla ANTES de que el cajero declare lo que
-- contó, sin que C# la calcule por su cuenta.
CREATE PROCEDURE Repuestos.sp_ObtenerMontoEsperadoCaja
    @SesionCajaId INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        sc.MontoApertura + ISNULL((
            SELECT SUM(v.Total)
            FROM Repuestos.Ventas v
            WHERE v.SesionCajaId = sc.Id AND v.MetodoPago = 'Efectivo' AND v.Anulada = 0
        ), 0) AS MontoEsperado
    FROM Repuestos.SesionesCaja sc
    WHERE sc.Id = @SesionCajaId;
END
GO
