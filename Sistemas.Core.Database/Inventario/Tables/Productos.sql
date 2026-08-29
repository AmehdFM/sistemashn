CREATE TABLE Inventario.Productos (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    Codigo              NVARCHAR(30)    NOT NULL,
    Nombre              NVARCHAR(150)   NOT NULL,
    Descripcion         NVARCHAR(500)   NULL,
    PrecioUnitario      DECIMAL(12,2)   NOT NULL,
    CategoriaId         INT             NULL,
    TasaISV             DECIMAL(5,2)    NOT NULL DEFAULT 15.00,
    StockActual         INT             NOT NULL DEFAULT 0,
    StockMinimo         INT             NOT NULL DEFAULT 0,
    Activo              BIT             NOT NULL DEFAULT 1,
    FechaCreacion       DATETIME2(0)    NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_Productos_Codigo UNIQUE (Codigo),
    CONSTRAINT FK_Productos_Categorias FOREIGN KEY (CategoriaId) REFERENCES Inventario.Categorias(Id),
    CONSTRAINT CK_Productos_PrecioUnitario CHECK (PrecioUnitario >= 0),
    CONSTRAINT CK_Productos_TasaISV CHECK (TasaISV IN (0.00, 15.00, 18.00)),  -- tasas vigentes en Honduras: exento, general, especial
    CONSTRAINT CK_Productos_StockActual CHECK (StockActual >= 0),
    CONSTRAINT CK_Productos_StockMinimo CHECK (StockMinimo >= 0)
);
GO

CREATE INDEX IX_Productos_CategoriaId ON Inventario.Productos(CategoriaId);
CREATE INDEX IX_Productos_Activo ON Inventario.Productos(Activo);
GO
