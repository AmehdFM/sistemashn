CREATE PROCEDURE Repuestos.sp_AgregarNumeroEquivalente
    @ProductoId INT,
    @NumeroOEM  NVARCHAR(50),
    @Fabricante NVARCHAR(50) = NULL,
    @UsuarioId  INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El producto especificado no existe' AS Mensaje, CAST(NULL AS INT) AS NumeroEquivalenteId;
            RETURN;
        END

        IF @NumeroOEM IS NULL OR LEN(LTRIM(RTRIM(@NumeroOEM))) = 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El número OEM no puede estar vacío' AS Mensaje, CAST(NULL AS INT) AS NumeroEquivalenteId;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoNumeroEquivalente;

        INSERT INTO Repuestos.NumeroEquivalente (ProductoId, NumeroOEM, Fabricante)
        VALUES (@ProductoId, @NumeroOEM, @Fabricante);

        DECLARE @NumeroEquivalenteId INT = SCOPE_IDENTITY();

        IF @TranPropia = 1 COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@NumeroEquivalenteId AS NVARCHAR(50));

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = @UsuarioId,
            @Accion        = 'AGREGAR_NUMERO_EQUIVALENTE',
            @TablaAfectada = 'Repuestos.NumeroEquivalente',
            @RegistroId    = @RegistroIdAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Número equivalente agregado correctamente' AS Mensaje, @NumeroEquivalenteId AS NumeroEquivalenteId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoNumeroEquivalente;
        END

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ese número OEM ya está registrado para este producto' AS Mensaje, CAST(NULL AS INT) AS NumeroEquivalenteId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS NumeroEquivalenteId;
    END CATCH
END
GO
