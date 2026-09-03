-- Adelantada de la Fase 6: sp_RegistrarCompra (Fase 3) inserta acá cuando
-- @EsCredito = 1, así que la tabla debe existir para que ese SP compile,
-- aunque los SPs de pago/listado de esta tabla se completan en la Fase 6.
--
-- 'Vencida' no es un estado guardado: se calcularía al consultar
-- (SaldoPendiente > 0 AND FechaVencimiento < hoy) para no depender de un
-- proceso diario — Express no tiene SQL Server Agent.
CREATE TABLE Repuestos.CuentasPorPagar (
    Id                  INT             IDENTITY(1,1) NOT NULL,
    CompraId            INT             NOT NULL,
    MontoOriginal       DECIMAL(12,2)   NOT NULL,
    SaldoPendiente      DECIMAL(12,2)   NOT NULL,
    FechaVencimiento    DATE            NOT NULL,
    Estado              NVARCHAR(20)    NOT NULL CONSTRAINT DF_CuentasPorPagar_Estado DEFAULT 'Pendiente',
    CONSTRAINT PK_CuentasPorPagar PRIMARY KEY (Id),
    CONSTRAINT UQ_CuentasPorPagar_CompraId UNIQUE (CompraId),
    CONSTRAINT FK_CuentasPorPagar_Compras FOREIGN KEY (CompraId) REFERENCES Repuestos.Compras(Id),
    CONSTRAINT CK_CuentasPorPagar_Montos CHECK (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal),
    CONSTRAINT CK_CuentasPorPagar_MontoOriginal CHECK (MontoOriginal > 0),
    CONSTRAINT CK_CuentasPorPagar_Estado CHECK (Estado IN ('Pendiente', 'PagadaParcial', 'Pagada', 'Anulada'))
);
GO

CREATE INDEX IX_CuentasPorPagar_Vencimiento
    ON Repuestos.CuentasPorPagar(FechaVencimiento)
    WHERE SaldoPendiente > 0;
GO
