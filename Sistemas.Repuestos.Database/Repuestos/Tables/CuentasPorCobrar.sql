-- Adelantada de la Fase 6: sp_RegistrarVenta y sp_AnularVenta (Fase 5)
-- necesitan esta tabla para el crédito y para la decisión D-4; los SPs de
-- pago/listado de esta tabla se completan en la Fase 6.
--
-- 'Vencida' no es un estado guardado: se calcula al consultar
-- (SaldoPendiente > 0 AND FechaVencimiento < hoy) — Express no tiene
-- SQL Server Agent para un proceso diario que la actualice.
CREATE TABLE Repuestos.CuentasPorCobrar (
    Id                  INT             IDENTITY(1,1) NOT NULL,
    VentaId             INT             NOT NULL,
    MontoOriginal       DECIMAL(12,2)   NOT NULL,
    SaldoPendiente      DECIMAL(12,2)   NOT NULL,
    FechaVencimiento    DATE            NOT NULL,
    Estado              NVARCHAR(20)    NOT NULL CONSTRAINT DF_CuentasPorCobrar_Estado DEFAULT 'Pendiente',
    CONSTRAINT PK_CuentasPorCobrar PRIMARY KEY (Id),
    CONSTRAINT UQ_CuentasPorCobrar_VentaId UNIQUE (VentaId),
    CONSTRAINT FK_CuentasPorCobrar_Ventas FOREIGN KEY (VentaId) REFERENCES Repuestos.Ventas(Id),
    CONSTRAINT CK_CuentasPorCobrar_Montos CHECK (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal),
    CONSTRAINT CK_CuentasPorCobrar_MontoOriginal CHECK (MontoOriginal > 0),
    -- 'Anulada' permite cerrar la cuenta cuando se anula la venta que la originó (D-4)
    CONSTRAINT CK_CuentasPorCobrar_Estado CHECK (Estado IN ('Pendiente', 'PagadaParcial', 'Pagada', 'Anulada'))
);
GO

CREATE INDEX IX_CuentasPorCobrar_Vencimiento
    ON Repuestos.CuentasPorCobrar(FechaVencimiento)
    WHERE SaldoPendiente > 0;
GO
