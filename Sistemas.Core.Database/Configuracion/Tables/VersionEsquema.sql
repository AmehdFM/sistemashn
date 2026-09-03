-- Decisión D-2: sin esto no hay forma de saber en qué versión está cada
-- instalación offline ni de aplicar actualizaciones con confianza. Se
-- actualiza en el script post-despliegue de cada publicación.
CREATE TABLE Configuracion.VersionEsquema (
    Id              INT             IDENTITY(1,1) NOT NULL,
    Version         NVARCHAR(20)    NOT NULL,   -- '1.0.0'
    Vertical        NVARCHAR(50)    NOT NULL,   -- 'Core' | 'Repuestos'
    FechaAplicacion DATETIME2(0)    NOT NULL CONSTRAINT DF_VersionEsquema_Fecha DEFAULT SYSDATETIME(),
    CONSTRAINT PK_VersionEsquema PRIMARY KEY (Id),
    CONSTRAINT UQ_VersionEsquema UNIQUE (Vertical, Version)
);
GO
