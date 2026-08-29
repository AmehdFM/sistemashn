CREATE TABLE Facturacion.ConfiguracionCAI (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    RangoAutorizado     NVARCHAR(40)  NOT NULL,   -- formato oficial del CAI otorgado por el SAR
    RangoInicial        CHAR(16)      NOT NULL,
    RangoFinal          CHAR(16)      NOT NULL,
    CorrelativoActual   CHAR(16)      NOT NULL,
    FechaAutorizacion   DATE          NOT NULL,
    FechaVencimiento    DATE          NOT NULL,
    Activo              BIT           NOT NULL DEFAULT 1,
    CONSTRAINT CK_ConfiguracionCAI_RangoValido CHECK (RangoFinal > RangoInicial),
    CONSTRAINT CK_ConfiguracionCAI_CorrelativoEnRango CHECK (CorrelativoActual >= RangoInicial AND CorrelativoActual <= RangoFinal),
    CONSTRAINT CK_ConfiguracionCAI_Fechas CHECK (FechaVencimiento > FechaAutorizacion)
);
GO

-- Solo puede haber UN rango de CAI activo a la vez — índice único filtrado
CREATE UNIQUE INDEX UX_ConfiguracionCAI_UnicoActivo
    ON Facturacion.ConfiguracionCAI(Activo)
    WHERE Activo = 1;
GO
