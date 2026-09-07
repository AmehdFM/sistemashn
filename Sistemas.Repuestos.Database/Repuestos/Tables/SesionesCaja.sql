-- Una sola sesión de caja abierta a la vez (el sistema asume un solo punto
-- de venta, igual que el resto del sistema). Los campos de cierre se mueven
-- juntos igual que CK_Ventas_Anulacion: todos NULL mientras está Abierta,
-- todos llenos cuando se Cierra.
CREATE TABLE Repuestos.SesionesCaja (
    Id                      INT             IDENTITY(1,1) NOT NULL,
    UsuarioAperturaId       INT             NOT NULL,
    FechaApertura           DATETIME2(0)    NOT NULL CONSTRAINT DF_SesionesCaja_FechaApertura DEFAULT SYSDATETIME(),
    MontoApertura           DECIMAL(12,2)   NOT NULL,
    UsuarioCierreId         INT             NULL,
    FechaCierre             DATETIME2(0)    NULL,
    MontoCierreDeclarado    DECIMAL(12,2)   NULL,
    MontoCierreCalculado    DECIMAL(12,2)   NULL,
    Diferencia              DECIMAL(12,2)   NULL,
    Estado                  NVARCHAR(20)    NOT NULL CONSTRAINT DF_SesionesCaja_Estado DEFAULT 'Abierta',
    CONSTRAINT PK_SesionesCaja PRIMARY KEY (Id),
    CONSTRAINT FK_SesionesCaja_Usuarios_Apertura FOREIGN KEY (UsuarioAperturaId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT FK_SesionesCaja_Usuarios_Cierre FOREIGN KEY (UsuarioCierreId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_SesionesCaja_MontoApertura CHECK (MontoApertura >= 0),
    CONSTRAINT CK_SesionesCaja_Estado CHECK (Estado IN ('Abierta', 'Cerrada')),
    -- Los campos de cierre se mueven juntos: no puede existir una sesión
    -- cerrada sin sus datos de cierre, ni una sesión abierta que ya los tenga.
    CONSTRAINT CK_SesionesCaja_Cierre CHECK (
        (Estado = 'Abierta' AND UsuarioCierreId IS NULL AND FechaCierre IS NULL
            AND MontoCierreDeclarado IS NULL AND MontoCierreCalculado IS NULL AND Diferencia IS NULL)
     OR (Estado = 'Cerrada' AND UsuarioCierreId IS NOT NULL AND FechaCierre IS NOT NULL
            AND MontoCierreDeclarado IS NOT NULL AND MontoCierreCalculado IS NOT NULL AND Diferencia IS NOT NULL))
);
GO

CREATE INDEX IX_SesionesCaja_Estado ON Repuestos.SesionesCaja(Estado);
GO
