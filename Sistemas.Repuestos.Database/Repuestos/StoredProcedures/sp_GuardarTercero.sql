-- Alta o edición de tercero (proveedor y/o cliente). @TerceroId = NULL crea
-- uno nuevo; @TerceroId con valor edita el existente.
CREATE PROCEDURE Repuestos.sp_GuardarTercero
    @TerceroId   INT = NULL,
    @Nombre      NVARCHAR(150),
    @Empresa     NVARCHAR(150) = NULL,
    @Correo      NVARCHAR(150) = NULL,
    @Telefono    NVARCHAR(20) = NULL,
    @RTN         CHAR(14) = NULL,
    @EsProveedor BIT = 0,
    @EsCliente   BIT = 0,
    @Activo      BIT = 1,
    @UsuarioId   INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF @RTN IS NOT NULL AND (LEN(@RTN) <> 14 OR @RTN LIKE '%[^0-9]%')
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El RTN debe tener exactamente 14 dígitos numéricos' AS Mensaje, CAST(NULL AS INT) AS TerceroId;
            RETURN;
        END

        IF @EsProveedor = 0 AND @EsCliente = 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Debe marcar al menos un rol (proveedor o cliente)' AS Mensaje, CAST(NULL AS INT) AS TerceroId;
            RETURN;
        END

        IF @TerceroId IS NULL
        BEGIN
            IF EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Nombre = @Nombre)
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un tercero con ese nombre' AS Mensaje, CAST(NULL AS INT) AS TerceroId;
                RETURN;
            END
        END
        ELSE
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Id = @TerceroId)
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'El tercero especificado no existe' AS Mensaje, CAST(NULL AS INT) AS TerceroId;
                RETURN;
            END

            IF EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Nombre = @Nombre AND Id <> @TerceroId)
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'Ya existe otro tercero con ese nombre' AS Mensaje, CAST(NULL AS INT) AS TerceroId;
                RETURN;
            END
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoTercero;

        IF @TerceroId IS NULL
        BEGIN
            INSERT INTO Repuestos.Terceros (Nombre, Empresa, Correo, Telefono, RTN, EsProveedor, EsCliente, Activo)
            VALUES (@Nombre, @Empresa, @Correo, @Telefono, @RTN, @EsProveedor, @EsCliente, @Activo);

            SET @TerceroId = SCOPE_IDENTITY();
        END
        ELSE
        BEGIN
            UPDATE Repuestos.Terceros
            SET Nombre      = @Nombre,
                Empresa     = @Empresa,
                Correo      = @Correo,
                Telefono    = @Telefono,
                RTN         = @RTN,
                EsProveedor = @EsProveedor,
                EsCliente   = @EsCliente,
                Activo      = @Activo
            WHERE Id = @TerceroId;
        END

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@TerceroId AS NVARCHAR(50));

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'GUARDAR_TERCERO',
            @TablaAfectada = 'Repuestos.Terceros',
            @RegistroId    = @RegistroIdAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Tercero guardado correctamente' AS Mensaje, @TerceroId AS TerceroId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoTercero;
        END

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un tercero con ese nombre' AS Mensaje, CAST(NULL AS INT) AS TerceroId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS TerceroId;
    END CATCH
END
GO
