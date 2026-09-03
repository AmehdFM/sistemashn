-- Alta o edición de proveedor. @ProveedorId = NULL crea uno nuevo;
-- @ProveedorId con valor edita el existente.
CREATE PROCEDURE Repuestos.sp_GuardarProveedor
    @ProveedorId INT = NULL,
    @Nombre      NVARCHAR(150),
    @RTN         CHAR(14) = NULL,
    @Telefono    NVARCHAR(20) = NULL,
    @Contacto    NVARCHAR(100) = NULL,
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
            SELECT CAST(0 AS BIT) AS Exito, 'El RTN debe tener exactamente 14 dígitos numéricos' AS Mensaje, CAST(NULL AS INT) AS ProveedorId;
            RETURN;
        END

        IF @ProveedorId IS NULL
        BEGIN
            IF EXISTS (SELECT 1 FROM Repuestos.Proveedores WHERE Nombre = @Nombre)
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un proveedor con ese nombre' AS Mensaje, CAST(NULL AS INT) AS ProveedorId;
                RETURN;
            END
        END
        ELSE
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM Repuestos.Proveedores WHERE Id = @ProveedorId)
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'El proveedor especificado no existe' AS Mensaje, CAST(NULL AS INT) AS ProveedorId;
                RETURN;
            END

            IF EXISTS (SELECT 1 FROM Repuestos.Proveedores WHERE Nombre = @Nombre AND Id <> @ProveedorId)
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito, 'Ya existe otro proveedor con ese nombre' AS Mensaje, CAST(NULL AS INT) AS ProveedorId;
                RETURN;
            END
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoProveedor;

        IF @ProveedorId IS NULL
        BEGIN
            INSERT INTO Repuestos.Proveedores (Nombre, RTN, Telefono, Contacto, Activo)
            VALUES (@Nombre, @RTN, @Telefono, @Contacto, @Activo);

            SET @ProveedorId = SCOPE_IDENTITY();
        END
        ELSE
        BEGIN
            UPDATE Repuestos.Proveedores
            SET Nombre   = @Nombre,
                RTN      = @RTN,
                Telefono = @Telefono,
                Contacto = @Contacto,
                Activo   = @Activo
            WHERE Id = @ProveedorId;
        END

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@ProveedorId AS NVARCHAR(50));

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'GUARDAR_PROVEEDOR',
            @TablaAfectada = 'Repuestos.Proveedores',
            @RegistroId    = @RegistroIdAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Proveedor guardado correctamente' AS Mensaje, @ProveedorId AS ProveedorId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoProveedor;
        END

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe un proveedor con ese nombre' AS Mensaje, CAST(NULL AS INT) AS ProveedorId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS ProveedorId;
    END CATCH
END
GO
