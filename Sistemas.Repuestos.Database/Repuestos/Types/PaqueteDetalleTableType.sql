CREATE TYPE Repuestos.PaqueteDetalleTableType AS TABLE (
    ComponenteProductoId    INT NOT NULL,
    Cantidad                DECIMAL(12,2) NOT NULL
);
GO
