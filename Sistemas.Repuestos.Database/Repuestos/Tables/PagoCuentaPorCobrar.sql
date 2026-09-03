-- Adelantada de la Fase 6: sp_AnularVenta (Fase 5) necesita saber si una
-- cuenta por cobrar ya tiene pagos (decisión D-4). Los SPs de pago/listado
-- se completan en la Fase 6.
CREATE TABLE Repuestos.PagoCuentaPorCobrar (
    Id                  INT             IDENTITY(1,1) NOT NULL,
    CuentaPorCobrarId   INT             NOT NULL,
    Monto               DECIMAL(12,2)   NOT NULL,
    Fecha               DATETIME2(0)    NOT NULL CONSTRAINT DF_PagoCPC_Fecha DEFAULT SYSDATETIME(),
    MetodoPago          NVARCHAR(30)    NULL,
    UsuarioId           INT             NOT NULL,
    CONSTRAINT PK_PagoCuentaPorCobrar PRIMARY KEY (Id),
    CONSTRAINT FK_PagoCPC_CuentaPorCobrar FOREIGN KEY (CuentaPorCobrarId) REFERENCES Repuestos.CuentasPorCobrar(Id),
    CONSTRAINT FK_PagoCPC_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_PagoCPC_Monto CHECK (Monto > 0)
);
GO

CREATE INDEX IX_PagoCPC_CuentaPorCobrarId ON Repuestos.PagoCuentaPorCobrar(CuentaPorCobrarId);
GO
