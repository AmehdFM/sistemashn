CREATE TABLE Security.Usuarios (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    NombreUsuario   NVARCHAR(50)   NOT NULL,
    PasswordHash    NVARCHAR(255)  NOT NULL,   -- hash tipo BCrypt (incluye salt embebido), nunca texto plano
    NombreCompleto  NVARCHAR(100)  NOT NULL,
    RolId           INT            NOT NULL,
    Activo          BIT            NOT NULL DEFAULT 1,
    FechaCreacion   DATETIME2(0)   NOT NULL DEFAULT SYSDATETIME(),
    UltimoAcceso    DATETIME2(0)   NULL,
    CONSTRAINT UQ_Usuarios_NombreUsuario UNIQUE (NombreUsuario),
    CONSTRAINT FK_Usuarios_Roles FOREIGN KEY (RolId) REFERENCES Security.Roles(Id),
    CONSTRAINT CK_Usuarios_NombreUsuario_Longitud CHECK (LEN(NombreUsuario) >= 3)
);
GO

CREATE INDEX IX_Usuarios_RolId ON Security.Usuarios(RolId);
GO
