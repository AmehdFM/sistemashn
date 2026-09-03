CREATE PROCEDURE Inventario.sp_CrearCategoria
    @Nombre NVARCHAR(100),
    @CategoriaPadreId INT = NULL,
    @UsuarioId INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        IF @CategoriaPadreId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM Inventario.Categorias WHERE Id = @CategoriaPadreId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La categoría padre especificada no existe' AS Mensaje, NULL AS CategoriaId;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM Inventario.Categorias WHERE Nombre = @Nombre AND ((CategoriaPadreId = @CategoriaPadreId) OR (CategoriaPadreId IS NULL AND @CategoriaPadreId IS NULL)))
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe una categoría con el mismo nombre bajo el mismo padre' AS Mensaje, NULL AS CategoriaId;
            RETURN;
        END

        -- Defecto B-10: un CHECK solo bloquea A->A, no A->B->A, porque no puede
        -- recorrer la jerarquía. Una categoría nueva nunca puede cerrar un ciclo
        -- por sí misma (todavía no existe en el árbol), pero esta misma validación
        -- es la que reutilizará el futuro sp_ActualizarCategoria, donde reparentar
        -- una categoría existente sí puede formar un ciclo. Se deja aquí para que
        -- ambos SPs compartan el mismo criterio y para detectar temprano una
        -- jerarquía ya corrupta antes de colgar de ella una categoría más.
        --
        -- El CTE recursivo no puede ir anidado dentro de un EXISTS(...): en
        -- T-SQL, WITH debe ser la primera instrucción de su propio statement.
        -- Por eso se resuelve aparte, en una variable, antes de usarlo.
        IF @CategoriaPadreId IS NOT NULL
        BEGIN
            DECLARE @CicloDetectado BIT = 0;

            ;WITH Ancestros AS (
                SELECT Id, CategoriaPadreId, 1 AS Nivel
                FROM Inventario.Categorias
                WHERE Id = @CategoriaPadreId

                UNION ALL

                SELECT c.Id, c.CategoriaPadreId, a.Nivel + 1
                FROM Inventario.Categorias c
                INNER JOIN Ancestros a ON c.Id = a.CategoriaPadreId
                WHERE a.Nivel < 100   -- freno de seguridad: una jerarquía sana nunca llega a 100 niveles
            )
            SELECT TOP (1) @CicloDetectado = 1
            FROM Ancestros
            WHERE Nivel >= 100;

            IF @CicloDetectado = 1
            BEGIN
                SELECT CAST(0 AS BIT) AS Exito,
                       'La categoría padre pertenece a una jerarquía inválida (ciclo detectado)' AS Mensaje,
                       NULL AS CategoriaId;
                RETURN;
            END
        END

        BEGIN TRAN;

        INSERT INTO Inventario.Categorias (Nombre, CategoriaPadreId, Activo)
        VALUES (@Nombre, @CategoriaPadreId, 1);

        DECLARE @CategoriaId INT = SCOPE_IDENTITY();

        COMMIT;

        -- EXEC solo acepta una constante o una variable como valor de
        -- parámetro, nunca una expresión: hay que resolverla antes.
        DECLARE @RegistroIdAuditoria NVARCHAR(50) = CAST(@CategoriaId AS NVARCHAR(50));
        DECLARE @DetalleAuditoria NVARCHAR(500) = 'Categoría creada: ' + @Nombre;

        -- Auditoría DESPUÉS del commit (defecto B-9): si falla, la categoría
        -- ya quedó guardada y no se pierde por un problema de auditoría.
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId,
            @Accion = 'CREAR_CATEGORIA',
            @TablaAfectada = 'Inventario.Categorias',
            @RegistroId = @RegistroIdAuditoria,
            @Detalle = @DetalleAuditoria;

        SELECT CAST(1 AS BIT) AS Exito, 'Categoría creada correctamente' AS Mensaje, @CategoriaId AS CategoriaId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;

        IF ERROR_NUMBER() IN (2627, 2601)
            SELECT CAST(0 AS BIT) AS Exito, 'Ya existe una categoría con el mismo nombre bajo el mismo padre' AS Mensaje, NULL AS CategoriaId;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, NULL AS CategoriaId;
    END CATCH
END
GO
