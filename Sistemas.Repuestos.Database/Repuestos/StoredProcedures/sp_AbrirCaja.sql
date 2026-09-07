-- Abre una sesión de caja nueva. Solo puede haber una sesión Abierta a la
-- vez (una sola caja/terminal, igual que el resto del sistema asume un solo
-- punto de venta) — sp_RegistrarVenta exige que exista una sesión Abierta
-- para cobrar al contado.
CREATE PROCEDURE Repuestos.sp_AbrirCaja
    @UsuarioId      INT,
    @MontoApertura  DECIMAL(12,2)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @SesionCajaId INT;

    BEGIN TRY
        IF @MontoApertura < 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El monto de apertura no puede ser negativo' AS Mensaje,
                   CAST(NULL AS INT) AS SesionCajaId;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM Repuestos.SesionesCaja WHERE Estado = 'Abierta')
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Ya hay una caja abierta' AS Mensaje,
                   CAST(NULL AS INT) AS SesionCajaId;
            RETURN;
        END

        BEGIN TRAN;

        -- Re-validar dentro de la transacción: dos aperturas simultáneas
        -- podrían pasar ambas el chequeo de arriba (misma razón que
        -- sp_RegistrarVenta re-valida stock con UPDLOCK).
        IF EXISTS (SELECT 1 FROM Repuestos.SesionesCaja WITH (UPDLOCK, HOLDLOCK) WHERE Estado = 'Abierta')
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'Ya hay una caja abierta' AS Mensaje,
                   CAST(NULL AS INT) AS SesionCajaId;
            RETURN;
        END

        INSERT INTO Repuestos.SesionesCaja (UsuarioAperturaId, FechaApertura, MontoApertura, Estado)
        VALUES (@UsuarioId, SYSDATETIME(), @MontoApertura, 'Abierta');

        SET @SesionCajaId = SCOPE_IDENTITY();

        COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'CAJA_ABIERTA',
            @TablaAfectada = 'Repuestos.SesionesCaja', @RegistroId = @SesionCajaId;

        SELECT CAST(1 AS BIT) AS Exito, 'Caja abierta correctamente' AS Mensaje, @SesionCajaId AS SesionCajaId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS SesionCajaId;
    END CATCH
END
GO
