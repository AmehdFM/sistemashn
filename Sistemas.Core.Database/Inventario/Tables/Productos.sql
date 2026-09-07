CREATE TABLE Inventario.Productos (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    Codigo              NVARCHAR(30)    NOT NULL,
    CodigoBarra         NVARCHAR(30)    NULL,
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
    CONSTRAINT UQ_Productos_CodigoBarra UNIQUE (CodigoBarra),
    CONSTRAINT FK_Productos_Categorias FOREIGN KEY (CategoriaId) REFERENCES Inventario.Categorias(Id),
    CONSTRAINT CK_Productos_PrecioUnitario CHECK (PrecioUnitario >= 0),
    CONSTRAINT CK_Productos_TasaISV CHECK (TasaISV IN (0.00, 15.00, 18.00)),  -- tasas vigentes en Honduras: exento, general, especial
    CONSTRAINT CK_Productos_StockActual CHECK (StockActual >= 0),
    CONSTRAINT CK_Productos_StockMinimo CHECK (StockMinimo >= 0)
);
GO

CREATE INDEX IX_Productos_CategoriaId ON Inventario.Productos(CategoriaId);
GO

-- Reemplaza al antiguo IX_Productos_Activo (defecto C-2): un índice sobre un
-- BIT con ~95% de filas activas no aporta selectividad y el optimizador
-- prefiere el scan de todos modos. Este índice filtrado cubre la consulta
-- real de búsqueda (por Nombre, solo activos) sin necesitar key lookup.
CREATE INDEX IX_Productos_Activo_Nombre
    ON Inventario.Productos(Nombre)
    INCLUDE (Codigo, PrecioUnitario, StockActual, StockMinimo, CategoriaId, TasaISV)
    WHERE Activo = 1;
GO
