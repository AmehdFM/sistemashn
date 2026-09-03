-- Estructuralmente idéntica a Repuestos.PagoCuentaPorCobrar, cambiando
-- CuentaPorCobrarId -> CuentaPorPagarId y la FK hacia Repuestos.CuentasPorPagar.
CREATE TABLE Repuestos.PagoCuentaPorPagar (
    Id                  INT             IDENTITY(1,1) NOT NULL,
    CuentaPorPagarId    INT             NOT NULL,
    Monto               DECIMAL(12,2)   NOT NULL,
    Fecha               DATETIME2(0)    NOT NULL CONSTRAINT DF_PagoCPP_Fecha DEFAULT SYSDATETIME(),
    MetodoPago          NVARCHAR(30)    NULL,
    UsuarioId           INT             NOT NULL,
    CONSTRAINT PK_PagoCuentaPorPagar PRIMARY KEY (Id),
    CONSTRAINT FK_PagoCPP_CuentaPorPagar FOREIGN KEY (CuentaPorPagarId) REFERENCES Repuestos.CuentasPorPagar(Id),
    CONSTRAINT FK_PagoCPP_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_PagoCPP_Monto CHECK (Monto > 0)
);
GO

CREATE INDEX IX_PagoCPP_CuentaPorPagarId ON Repuestos.PagoCuentaPorPagar(CuentaPorPagarId);
GO
