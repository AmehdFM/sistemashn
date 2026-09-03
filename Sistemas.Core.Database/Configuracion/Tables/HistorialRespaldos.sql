-- Gap no cubierto por el plan original: sp_VerificarEstadoSistema (sección 7)
-- necesita responder "¿cuándo fue el último respaldo exitoso?", pero el
-- respaldo en sí (BACKUP DATABASE, RESTORE VERIFYONLY) lo ejecuta C#/SMO
-- desde Sistemas.Mantenimiento, no T-SQL. Esta tabla es el único rastro que
-- le permite a la base responder esa pregunta sin tocar el sistema de
-- archivos. Se escribe vía Configuracion.sp_RegistrarResultadoRespaldo,
-- llamado después de cada intento de respaldo, exitoso o no.
CREATE TABLE Configuracion.HistorialRespaldos (
    Id              INT             IDENTITY(1,1) NOT NULL,
    FechaRespaldo   DATETIME2(0)    NOT NULL CONSTRAINT DF_HistorialRespaldos_Fecha DEFAULT SYSDATETIME(),
    Exito           BIT             NOT NULL,
    RutaDestino     NVARCHAR(260)   NULL,
    TamanoBytes     BIGINT          NULL,
    Mensaje         NVARCHAR(500)   NULL,
    CONSTRAINT PK_HistorialRespaldos PRIMARY KEY (Id)
);
GO

CREATE INDEX IX_HistorialRespaldos_FechaRespaldo
    ON Configuracion.HistorialRespaldos(FechaRespaldo DESC)
    WHERE Exito = 1;
GO
