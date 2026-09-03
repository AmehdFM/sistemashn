CREATE TABLE Repuestos.Compras (
    Id                      INT             IDENTITY(1,1) NOT NULL,
    ProveedorId             INT             NOT NULL,
    NumeroFacturaProveedor  NVARCHAR(30)    NULL,
    Fecha                   DATETIME2(0)    NOT NULL CONSTRAINT DF_Compras_Fecha DEFAULT SYSDATETIME(),
    Total                   DECIMAL(12,2)   NOT NULL CONSTRAINT DF_Compras_Total DEFAULT 0,
    UsuarioId               INT             NOT NULL,
    EsCredito               BIT             NOT NULL CONSTRAINT DF_Compras_EsCredito DEFAULT 0,
    CONSTRAINT PK_Compras PRIMARY KEY (Id),
    CONSTRAINT FK_Compras_Proveedores FOREIGN KEY (ProveedorId) REFERENCES Repuestos.Proveedores(Id),
    CONSTRAINT FK_Compras_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_Compras_Total CHECK (Total >= 0)
);
GO

CREATE INDEX IX_Compras_ProveedorId ON Repuestos.Compras(ProveedorId);
GO

CREATE INDEX IX_Compras_Fecha ON Repuestos.Compras(Fecha DESC);
GO
