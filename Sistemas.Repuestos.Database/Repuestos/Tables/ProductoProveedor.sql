-- PK compuesta: cubre "qué proveedores me venden este producto".
-- El índice extra cubre la dirección contraria: "qué me vende este proveedor".
CREATE TABLE Repuestos.ProductoProveedor (
    ProductoId      INT             NOT NULL,
    ProveedorId     INT             NOT NULL,
    PrecioCompra    DECIMAL(12,2)   NOT NULL,
    CONSTRAINT PK_ProductoProveedor PRIMARY KEY (ProductoId, ProveedorId),
    CONSTRAINT FK_ProductoProveedor_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT FK_ProductoProveedor_Terceros FOREIGN KEY (ProveedorId) REFERENCES Repuestos.Terceros(Id),
    CONSTRAINT CK_ProductoProveedor_Precio CHECK (PrecioCompra >= 0)
);
GO

CREATE INDEX IX_ProductoProveedor_ProveedorId ON Repuestos.ProductoProveedor(ProveedorId);
GO
