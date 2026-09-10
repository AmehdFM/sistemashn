CREATE TABLE Repuestos.Terceros (
    Id          INT             IDENTITY(1,1) NOT NULL,
    Nombre      NVARCHAR(150)   NOT NULL,
    Empresa     NVARCHAR(150)   NULL,
    Correo      NVARCHAR(150)   NULL,
    Telefono    NVARCHAR(20)    NULL,
    RTN         CHAR(14)        NULL,
    EsProveedor BIT             NOT NULL CONSTRAINT DF_Terceros_EsProveedor DEFAULT 0,
    EsCliente   BIT             NOT NULL CONSTRAINT DF_Terceros_EsCliente DEFAULT 0,
    Activo      BIT             NOT NULL CONSTRAINT DF_Terceros_Activo DEFAULT 1,
    CONSTRAINT PK_Terceros PRIMARY KEY (Id),
    CONSTRAINT UQ_Terceros_Nombre UNIQUE (Nombre),
    CONSTRAINT CK_Terceros_RTN CHECK (RTN IS NULL OR (LEN(RTN) = 14 AND RTN NOT LIKE '%[^0-9]%')),
    CONSTRAINT CK_Terceros_Correo CHECK (Correo IS NULL OR Correo LIKE '%_@_%._%'),
    CONSTRAINT CK_Terceros_AlMenosUnRol CHECK (EsProveedor = 1 OR EsCliente = 1)
);
GO

-- Mismo patrón que IX_Productos_Activo_Nombre: índice filtrado sobre la
-- columna de orden, para la combinación filtro-por-rol + orden-por-nombre
-- que hace sp_ListarProveedores, sin necesitar key lookup.
CREATE INDEX IX_Terceros_EsProveedor_Nombre
    ON Repuestos.Terceros(Nombre)
    INCLUDE (Empresa, Correo, Telefono, RTN, EsProveedor, EsCliente, Activo)
    WHERE EsProveedor = 1;
GO

-- Mismo patrón, para sp_ListarClientes.
CREATE INDEX IX_Terceros_EsCliente_Nombre
    ON Repuestos.Terceros(Nombre)
    INCLUDE (Empresa, Correo, Telefono, RTN, EsProveedor, EsCliente, Activo)
    WHERE EsCliente = 1;
GO
