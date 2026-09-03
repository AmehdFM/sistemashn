CREATE TABLE Auditoria.Auditoria (
    Id              BIGINT IDENTITY(1,1) PRIMARY KEY,   -- BIGINT: esta tabla crece indefinidamente
    UsuarioId       INT            NULL,                -- NULL permitido: eventos sin sesión (ej. login fallido de usuario inexistente)
    Accion          NVARCHAR(50)   NOT NULL,
    TablaAfectada   NVARCHAR(100)  NULL,
    RegistroId      NVARCHAR(50)   NULL,                -- como texto: distintas verticales usan distintos tipos de Id
    Detalle         NVARCHAR(500)  NULL,
    FechaHora       DATETIME2(0)   NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Auditoria_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id)
);
GO

CREATE INDEX IX_Auditoria_FechaHora ON Auditoria.Auditoria(FechaHora DESC);
GO

CREATE INDEX IX_Auditoria_UsuarioId ON Auditoria.Auditoria(UsuarioId);
GO
