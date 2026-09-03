-- Extensión 1:1 OPCIONAL de Inventario.Productos: ProductoId es PK y FK a
-- la vez. Opcional porque un insumo genérico (grasa, trapos) no tiene
-- número de parte. Toda consulta la ataca con LEFT JOIN, nunca INNER.
CREATE TABLE Repuestos.DetalleProducto (
    ProductoId      INT             NOT NULL,
    NumeroParte     NVARCHAR(50)    NULL,
    MarcaFabricante NVARCHAR(50)    NULL,
    EsOriginal      BIT             NOT NULL CONSTRAINT DF_DetalleProducto_EsOriginal DEFAULT 1,
    CONSTRAINT PK_DetalleProducto PRIMARY KEY (ProductoId),
    CONSTRAINT FK_DetalleProducto_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id)
);
GO

CREATE INDEX IX_DetalleProducto_NumeroParte
    ON Repuestos.DetalleProducto(NumeroParte)
    WHERE NumeroParte IS NOT NULL;
GO
