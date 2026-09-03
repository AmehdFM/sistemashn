CREATE TYPE Repuestos.CompraDetalleTableType AS TABLE (
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL
);
GO
