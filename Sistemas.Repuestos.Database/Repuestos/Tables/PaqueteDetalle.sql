-- La regla "un componente no puede ser a su vez un paquete" (sin paquetes
-- anidados) no puede expresarse en un CHECK porque requiere consultar otra
-- tabla; se valida en sp_ArmarPaquete.
CREATE TABLE Repuestos.PaqueteDetalle (
    Id                      INT IDENTITY(1,1) NOT NULL,
    PaqueteId               INT NOT NULL,
    ComponenteProductoId    INT NOT NULL,
    Cantidad                INT NOT NULL,
    CONSTRAINT PK_PaqueteDetalle PRIMARY KEY (Id),
    CONSTRAINT FK_PaqueteDetalle_Paquetes FOREIGN KEY (PaqueteId) REFERENCES Repuestos.Paquetes(ProductoId),
    CONSTRAINT FK_PaqueteDetalle_Productos FOREIGN KEY (ComponenteProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_PaqueteDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_PaqueteDetalle_NoAutoReferencia CHECK (ComponenteProductoId <> PaqueteId),
    CONSTRAINT UQ_PaqueteDetalle UNIQUE (PaqueteId, ComponenteProductoId)
);
GO

-- El UNIQUE (PaqueteId, ComponenteProductoId) ya cubre la expansión de
-- paquetes por PaqueteId; este índice cubre la dirección contraria (¿en qué
-- paquetes participa este componente?).
CREATE INDEX IX_PaqueteDetalle_ComponenteProductoId ON Repuestos.PaqueteDetalle(ComponenteProductoId);
GO
