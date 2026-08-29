CREATE TABLE Inventario.Etiquetas (
    Id      INT IDENTITY(1,1) PRIMARY KEY,
    Nombre  NVARCHAR(50) NOT NULL,
    CONSTRAINT UQ_Etiquetas_Nombre UNIQUE (Nombre)
);
GO
