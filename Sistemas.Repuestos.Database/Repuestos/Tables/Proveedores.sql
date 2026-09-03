CREATE TABLE Repuestos.Proveedores (
    Id          INT             IDENTITY(1,1) NOT NULL,
    Nombre      NVARCHAR(150)   NOT NULL,
    RTN         CHAR(14)        NULL,
    Telefono    NVARCHAR(20)    NULL,
    Contacto    NVARCHAR(100)   NULL,
    Activo      BIT             NOT NULL CONSTRAINT DF_Proveedores_Activo DEFAULT 1,
    CONSTRAINT PK_Proveedores PRIMARY KEY (Id),
    CONSTRAINT UQ_Proveedores_Nombre UNIQUE (Nombre),
    CONSTRAINT CK_Proveedores_RTN CHECK (RTN IS NULL OR (LEN(RTN) = 14 AND RTN NOT LIKE '%[^0-9]%'))
);
GO
