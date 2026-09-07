CREATE TABLE Repuestos.Ventas (
    Id              INT             IDENTITY(1,1) NOT NULL,
    NumeroFactura   NVARCHAR(60)    NOT NULL,   -- correlativo completo: 40 + 1 + 16 = 57
    Fecha           DATETIME2(0)    NOT NULL CONSTRAINT DF_Ventas_Fecha DEFAULT SYSDATETIME(),
    Subtotal        DECIMAL(12,2)   NOT NULL,
    MontoISV        DECIMAL(12,2)   NOT NULL,
    Total           DECIMAL(12,2)   NOT NULL,
    UsuarioId       INT             NOT NULL,
    ClienteId       INT             NULL,
    EsCredito       BIT             NOT NULL CONSTRAINT DF_Ventas_EsCredito DEFAULT 0,
    Anulada         BIT             NOT NULL CONSTRAINT DF_Ventas_Anulada DEFAULT 0,   -- nunca se hace DELETE: una factura con CAI emitido no se borra
    MotivoAnulacion NVARCHAR(200)   NULL,
    FechaAnulacion  DATETIME2(0)    NULL,
    SesionCajaId    INT             NULL,
    MetodoPago      NVARCHAR(20)    NOT NULL CONSTRAINT DF_Ventas_MetodoPago DEFAULT 'Efectivo',
    EfectivoRecibido DECIMAL(12,2)  NULL,
    Vuelto          DECIMAL(12,2)   NULL,
    CONSTRAINT PK_Ventas PRIMARY KEY (Id),
    CONSTRAINT UQ_Ventas_NumeroFactura UNIQUE (NumeroFactura),
    CONSTRAINT FK_Ventas_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT FK_Ventas_Terceros FOREIGN KEY (ClienteId) REFERENCES Repuestos.Terceros(Id),
    CONSTRAINT FK_Ventas_SesionesCaja FOREIGN KEY (SesionCajaId) REFERENCES Repuestos.SesionesCaja(Id),
    CONSTRAINT CK_Ventas_Subtotal CHECK (Subtotal >= 0),
    CONSTRAINT CK_Ventas_MontoISV CHECK (MontoISV >= 0),
    CONSTRAINT CK_Ventas_Total CHECK (Total >= 0),
    CONSTRAINT CK_Ventas_MetodoPago CHECK (MetodoPago IN ('Efectivo', 'Tarjeta', 'Transferencia')),
    -- Los tres campos de anulación se mueven juntos: no puede existir una
    -- venta anulada sin motivo ni fecha, ni un motivo en una venta viva.
    CONSTRAINT CK_Ventas_Anulacion CHECK (
        (Anulada = 0 AND MotivoAnulacion IS NULL AND FechaAnulacion IS NULL)
     OR (Anulada = 1 AND MotivoAnulacion IS NOT NULL AND FechaAnulacion IS NOT NULL))
);
GO

CREATE INDEX IX_Ventas_Fecha
    ON Repuestos.Ventas(Fecha DESC)
    INCLUDE (NumeroFactura, Total, UsuarioId)
    WHERE Anulada = 0;
GO

CREATE INDEX IX_Ventas_UsuarioId ON Repuestos.Ventas(UsuarioId);
GO

CREATE INDEX IX_Ventas_ClienteId ON Repuestos.Ventas(ClienteId);
GO
