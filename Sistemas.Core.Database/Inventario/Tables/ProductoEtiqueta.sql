CREATE TABLE Inventario.ProductoEtiqueta (
    ProductoId  INT NOT NULL,
    EtiquetaId  INT NOT NULL,
    CONSTRAINT PK_ProductoEtiqueta PRIMARY KEY (ProductoId, EtiquetaId),
    CONSTRAINT FK_ProductoEtiqueta_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT FK_ProductoEtiqueta_Etiquetas FOREIGN KEY (EtiquetaId) REFERENCES Inventario.Etiquetas(Id)
);
GO
