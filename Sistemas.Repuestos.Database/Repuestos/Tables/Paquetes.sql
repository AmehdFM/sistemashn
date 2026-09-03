-- Un paquete ES un producto de Inventario.Productos (tiene código, precio e
-- ISV propios) más esta fila que lo marca como tal. No tiene stock propio:
-- el stock que se mueve es el de sus componentes.
CREATE TABLE Repuestos.Paquetes (
    ProductoId  INT NOT NULL,
    CONSTRAINT PK_Paquetes PRIMARY KEY (ProductoId),
    CONSTRAINT FK_Paquetes_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id)
);
GO
