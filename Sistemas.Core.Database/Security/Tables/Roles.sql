CREATE TABLE Security.Roles (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    Nombre          NVARCHAR(50)  NOT NULL,
    Descripcion     NVARCHAR(200) NULL,
    CONSTRAINT UQ_Roles_Nombre UNIQUE (Nombre)
);
GO
