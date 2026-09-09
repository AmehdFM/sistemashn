-- Catálogo de unidades de medida (conteo, peso, longitud, área, volumen) en
-- sistema inglés e internacional. PermiteFraccion gobierna si Cantidad/Stock
-- se puede capturar con decimales para productos de esta unidad — todo se
-- guarda igual como DECIMAL(12,2), esta bandera solo cambia la validación y
-- el formato, no el tipo de columna. Vive en Core (no en Repuestos) porque
-- es un concepto genérico que cualquier vertical futura reutiliza, igual
-- que Productos.
CREATE TABLE Inventario.UnidadesMedida (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    Codigo          NVARCHAR(10)    NOT NULL,
    Nombre          NVARCHAR(50)    NOT NULL,
    Simbolo         NVARCHAR(10)    NOT NULL,
    PermiteFraccion BIT             NOT NULL DEFAULT 1,
    Sistema         NVARCHAR(20)    NULL,
    Activo          BIT             NOT NULL DEFAULT 1,
    CONSTRAINT UQ_UnidadesMedida_Codigo UNIQUE (Codigo)
);
GO
