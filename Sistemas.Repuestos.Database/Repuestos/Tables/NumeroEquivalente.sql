-- 1:N — números OEM de otros fabricantes que sirven para este producto. El
-- caso de uso central del rubro: "el cliente trae un número de otro
-- fabricante, ¿qué tengo que sirva?" — esa búsqueda tiene que ser instantánea,
-- de ahí el índice dedicado sobre NumeroOEM.
CREATE TABLE Repuestos.NumeroEquivalente (
    Id          INT             IDENTITY(1,1) NOT NULL,
    ProductoId  INT             NOT NULL,
    NumeroOEM   NVARCHAR(50)    NOT NULL,
    Fabricante  NVARCHAR(50)    NULL,
    CONSTRAINT PK_NumeroEquivalente PRIMARY KEY (Id),
    CONSTRAINT FK_NumeroEquivalente_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT UQ_NumeroEquivalente UNIQUE (ProductoId, NumeroOEM)
);
GO

CREATE INDEX IX_NumeroEquivalente_NumeroOEM
    ON Repuestos.NumeroEquivalente(NumeroOEM)
    INCLUDE (ProductoId, Fabricante);
GO
