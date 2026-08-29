CREATE TYPE Inventario.ProductoTableType AS TABLE (
    Codigo          NVARCHAR(30)   NOT NULL,
    Nombre          NVARCHAR(150)  NOT NULL,
    Descripcion     NVARCHAR(500)  NULL,
    PrecioUnitario  DECIMAL(12,2)  NOT NULL,
    CategoriaId     INT            NULL,
    TasaISV         DECIMAL(5,2)   NULL,
    StockMinimo     INT            NULL
);
GO
