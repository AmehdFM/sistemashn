-- PrecioUnitario y TasaISV son una FOTOGRAFÍA del producto al momento de
-- vender: si el precio o la tasa cambian después, las facturas ya emitidas
-- no cambian de valor retroactivamente.
CREATE TABLE Repuestos.VentaDetalle (
    Id              INT             IDENTITY(1,1) NOT NULL,
    VentaId         INT             NOT NULL,
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    PrecioUnitario  DECIMAL(12,2)   NOT NULL,
    TasaISV         DECIMAL(5,2)    NOT NULL,
    Subtotal        AS (Cantidad * PrecioUnitario) PERSISTED,
    CONSTRAINT PK_VentaDetalle PRIMARY KEY (Id),
    CONSTRAINT FK_VentaDetalle_Ventas FOREIGN KEY (VentaId) REFERENCES Repuestos.Ventas(Id),
    CONSTRAINT FK_VentaDetalle_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_VentaDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_VentaDetalle_Precio CHECK (PrecioUnitario >= 0),
    CONSTRAINT CK_VentaDetalle_TasaISV CHECK (TasaISV IN (0.00, 15.00, 18.00))
);
GO

CREATE INDEX IX_VentaDetalle_VentaId
    ON Repuestos.VentaDetalle(VentaId)
    INCLUDE (ProductoId, Cantidad, PrecioUnitario, TasaISV);
GO

CREATE INDEX IX_VentaDetalle_ProductoId ON Repuestos.VentaDetalle(ProductoId);
GO
