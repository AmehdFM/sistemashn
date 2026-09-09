-- Subtotal calculado y PERSISTED: un INSERT mal armado desde la app no puede
-- guardar un subtotal que no cuadre con Cantidad * CostoUnitario.
CREATE TABLE Repuestos.CompraDetalle (
    Id              INT             IDENTITY(1,1) NOT NULL,
    CompraId        INT             NOT NULL,
    ProductoId      INT             NOT NULL,
    Cantidad        DECIMAL(12,2)   NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL,
    -- CAST explícito: decimal(12,2) * decimal(12,2) subiría a escala 4 sin
    -- esto (regla de aritmética decimal de SQL Server), y Subtotal debe
    -- quedarse en 2 decimales igual que el resto del dinero del sistema.
    Subtotal        AS (CAST(Cantidad * CostoUnitario AS DECIMAL(12,2))) PERSISTED,
    CONSTRAINT PK_CompraDetalle PRIMARY KEY (Id),
    CONSTRAINT FK_CompraDetalle_Compras FOREIGN KEY (CompraId) REFERENCES Repuestos.Compras(Id),
    CONSTRAINT FK_CompraDetalle_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_CompraDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_CompraDetalle_Costo CHECK (CostoUnitario >= 0)
);
GO

CREATE INDEX IX_CompraDetalle_CompraId
    ON Repuestos.CompraDetalle(CompraId)
    INCLUDE (ProductoId, Cantidad, CostoUnitario);
GO

CREATE INDEX IX_CompraDetalle_ProductoId ON Repuestos.CompraDetalle(ProductoId);
GO
