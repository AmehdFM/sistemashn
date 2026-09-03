CREATE TABLE Configuracion.Configuracion (
    Id                  INT             NOT NULL,   -- sin IDENTITY: es un singleton, no genera identidades (defecto B-2)
    NombreComercial     NVARCHAR(150)   NOT NULL,
    RTN                 CHAR(14)        NOT NULL,
    Direccion           NVARCHAR(300)   NULL,
    Telefono            NVARCHAR(20)    NULL,
    CorreoContacto      NVARCHAR(100)   NULL,
    Logo                VARBINARY(MAX)  NULL,   -- imagen embebida, así viaja con el backup
    FechaActualizacion  DATETIME2(0)    NOT NULL CONSTRAINT DF_Configuracion_FechaActualizacion DEFAULT SYSDATETIME(),
    CONSTRAINT PK_Configuracion PRIMARY KEY (Id),
    CONSTRAINT CK_Configuracion_RTN_Formato CHECK (RTN NOT LIKE '%[^0-9]%' AND LEN(RTN) = 14),
    CONSTRAINT CK_Configuracion_Singleton CHECK (Id = 1)  -- fuerza que solo pueda existir la fila Id=1
);
GO
