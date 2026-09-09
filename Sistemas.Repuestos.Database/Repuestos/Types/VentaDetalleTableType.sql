CREATE TYPE Repuestos.VentaDetalleTableType AS TABLE (
    ProductoId  INT NOT NULL,
    Cantidad    DECIMAL(12,2) NOT NULL
);
GO
