CREATE TYPE Repuestos.CompraDetalleTableType AS TABLE (
    ProductoId      INT             NOT NULL,
    Cantidad        DECIMAL(12,2)   NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL
);
GO
