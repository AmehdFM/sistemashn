CREATE TABLE Inventario.Categorias (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    Nombre              NVARCHAR(100)  NOT NULL,
    CategoriaPadreId    INT            NULL,
    Activo              BIT            NOT NULL DEFAULT 1,
    CONSTRAINT FK_Categorias_CategoriaPadre FOREIGN KEY (CategoriaPadreId) REFERENCES Inventario.Categorias(Id),
    CONSTRAINT CK_Categorias_NoAutoReferencia CHECK (CategoriaPadreId <> Id),
    CONSTRAINT UQ_Categorias_NombrePorPadre UNIQUE (Nombre, CategoriaPadreId)
);
GO
