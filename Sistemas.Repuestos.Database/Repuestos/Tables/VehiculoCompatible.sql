-- 1:N — a qué vehículos le sirve un producto. La consulta real es
-- "¿qué tengo para un Corolla 2015?", por eso el índice va sobre (Marca, Modelo).
--
-- Corrección respecto al plan original: aquel definía
-- CHECK (AnioDesde BETWEEN 1950 AND YEAR(GETDATE()) + 1). GETDATE() no es
-- determinística y SQL Server no la admite en un CHECK — no compila. El
-- tope superior (año actual + 1) se valida en sp_AgregarVehiculoCompatible,
-- no en la tabla.
CREATE TABLE Repuestos.VehiculoCompatible (
    Id          INT             IDENTITY(1,1) NOT NULL,
    ProductoId  INT             NOT NULL,
    Marca       NVARCHAR(50)    NOT NULL,
    Modelo      NVARCHAR(50)    NOT NULL,
    AnioDesde   SMALLINT        NOT NULL,
    AnioHasta   SMALLINT        NOT NULL,
    CONSTRAINT PK_VehiculoCompatible PRIMARY KEY (Id),
    CONSTRAINT FK_VehiculoCompatible_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_VehiculoCompatible_Anios CHECK (AnioHasta >= AnioDesde),
    CONSTRAINT CK_VehiculoCompatible_AnioMinimo CHECK (AnioDesde >= 1950),
    CONSTRAINT UQ_VehiculoCompatible UNIQUE (ProductoId, Marca, Modelo, AnioDesde, AnioHasta)
);
GO

CREATE INDEX IX_VehiculoCompatible_MarcaModelo
    ON Repuestos.VehiculoCompatible(Marca, Modelo)
    INCLUDE (ProductoId, AnioDesde, AnioHasta);
GO

CREATE INDEX IX_VehiculoCompatible_ProductoId ON Repuestos.VehiculoCompatible(ProductoId);
GO
