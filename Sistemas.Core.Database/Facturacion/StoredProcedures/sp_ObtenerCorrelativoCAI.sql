CREATE PROCEDURE Facturacion.sp_ObtenerCorrelativoCAI
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRAN;

        DECLARE @Id INT, @RangoAutorizado NVARCHAR(40), @CorrelativoActual CHAR(16),
                @RangoFinal CHAR(16), @FechaVencimiento DATE;

        -- UPDLOCK + HOLDLOCK: bloquea la fila hasta el COMMIT, así una segunda
        -- llamada simultánea espera en vez de leer el mismo correlativo
        SELECT
            @Id = Id,
            @RangoAutorizado = RangoAutorizado,
            @CorrelativoActual = CorrelativoActual,
            @RangoFinal = RangoFinal,
            @FechaVencimiento = FechaVencimiento
        FROM Facturacion.ConfiguracionCAI WITH (UPDLOCK, HOLDLOCK)
        WHERE Activo = 1;

        IF @Id IS NULL
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'No hay un CAI activo configurado' AS Mensaje, NULL AS Correlativo;
            RETURN;
        END

        IF @FechaVencimiento < CAST(GETDATE() AS DATE)
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'El CAI configurado está vencido' AS Mensaje, NULL AS Correlativo;
            RETURN;
        END

        IF @CorrelativoActual >= @RangoFinal
        BEGIN
            ROLLBACK;
            SELECT CAST(0 AS BIT) AS Exito, 'El rango de CAI se agotó, contactar al administrador' AS Mensaje, NULL AS Correlativo;
            RETURN;
        END

        DECLARE @Siguiente CHAR(16) = RIGHT('0000000000000000' + CAST(CAST(@CorrelativoActual AS BIGINT) + 1 AS NVARCHAR(16)), 16);

        UPDATE Facturacion.ConfiguracionCAI
        SET CorrelativoActual = @Siguiente
        WHERE Id = @Id;

        COMMIT;
        SELECT CAST(1 AS BIT) AS Exito, 'OK' AS Mensaje, @RangoAutorizado + '-' + @Siguiente AS Correlativo;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS Correlativo;
    END CATCH
END
GO
