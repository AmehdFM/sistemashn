CREATE PROCEDURE Repuestos.sp_AgregarVehiculoCompatible
    @ProductoId INT,
    @Marca      NVARCHAR(50),
    @Modelo     NVARCHAR(50),
    @AnioDesde  SMALLINT,
    @AnioHasta  SMALLINT,
    @UsuarioId  INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El producto especificado no existe' AS Mensaje, CAST(NULL AS INT) AS VehiculoCompatibleId;
            RETURN;
        END

        IF @AnioHasta < @AnioDesde
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El año hasta no puede ser menor que el año desde' AS Mensaje, CAST(NULL AS INT) AS VehiculoCompatibleId;
            RETURN;
        END

        IF @AnioDesde < 1950
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El año desde no puede ser menor a 1950' AS Mensaje, CAST(NULL AS INT) AS VehiculoCompatibleId;
            RETURN;
        END

        -- El tope superior no puede ir en un CHECK (GETDATE/SYSDATETIME no
        -- son determinísticas y SQL Server las rechaza ahí); se valida acá.
        IF @AnioHasta > YEAR(SYSDATETIME()) + 1
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El año hasta no puede superar el año próximo' AS Mensaje, CAST(NULL AS INT) AS VehiculoCompatibleId;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoVehiculoCompatible;

        INSERT INTO Repuestos.VehiculoCompatible (ProductoId, Marca, Modelo, AnioDesde, AnioHasta)
        VALUES (@ProductoId, @Marca, @Modelo, @AnioDesde, @AnioHasta);

        DECLARE @VehiculoCompatibleId INT = SCOPE_IDENTITY();

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@VehiculoCompatibleId AS NVARCHAR(50));

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'AGREGAR_VEHICULO_COMPATIBLE',
            @TablaAfectada = 'Repuestos.VehiculoCompatible',
            @RegistroId    = @RegistroIdAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Vehículo compatible agregado correctamente' AS Mensaje, @VehiculoCompatibleId AS VehiculoCompatibleId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVehiculoCompatible;
        END

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ese rango de años para esta marca y modelo ya está registrado para el producto' AS Mensaje, CAST(NULL AS INT) AS VehiculoCompatibleId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS VehiculoCompatibleId;
    END CATCH
END
GO
