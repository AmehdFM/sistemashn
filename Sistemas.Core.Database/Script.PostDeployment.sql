-- ============================================================================
-- Script.PostDeployment.sql — Sistemas.Core.Database
--
-- Se ejecuta automáticamente después de cada Publish/Deploy de este proyecto
-- SSDT. Debe ser 100% idempotente: puede correr muchas veces sin duplicar
-- datos ni fallar si los datos ya existen.
-- ============================================================================

PRINT 'Sembrando roles base (Security.Roles)...';

IF NOT EXISTS (SELECT 1 FROM Security.Roles WHERE Nombre = N'Administrador')
    INSERT INTO Security.Roles (Nombre, Descripcion)
    VALUES (N'Administrador', N'Acceso total al sistema, incluida la administración de usuarios');

IF NOT EXISTS (SELECT 1 FROM Security.Roles WHERE Nombre = N'Usuario')
    INSERT INTO Security.Roles (Nombre, Descripcion)
    VALUES (N'Usuario', N'Acceso operativo estándar, sin administración de usuarios');
GO

PRINT 'Sembrando unidades de medida (Inventario.UnidadesMedida)...';

-- "Unidad" se fuerza a Id = 1 porque Productos.UnidadMedidaId usa
-- DEFAULT 1 como valor literal simple (no una subconsulta).
IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'UNI')
BEGIN
    SET IDENTITY_INSERT Inventario.UnidadesMedida ON;
    INSERT INTO Inventario.UnidadesMedida (Id, Codigo, Nombre, Simbolo, PermiteFraccion, Sistema)
    VALUES (1, N'UNI', N'Unidad', N'u', 0, N'Conteo');
    SET IDENTITY_INSERT Inventario.UnidadesMedida OFF;
END

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'DOC')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'DOC', N'Docena', N'doc', 0, N'Conteo');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'PAR')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'PAR', N'Par', N'par', 0, N'Conteo');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'LB')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'LB', N'Libra', N'lb', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'OZ')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'OZ', N'Onza', N'oz', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'QQ')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'QQ', N'Quintal', N'qq', 1, N'Otro');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'KG')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'KG', N'Kilogramo', N'kg', 1, N'Metrico');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'GR')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'GR', N'Gramo', N'g', 1, N'Metrico');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'PIE')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'PIE', N'Pie', N'ft', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'PLG')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'PLG', N'Pulgada', N'in', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'YDA')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'YDA', N'Yarda', N'yd', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'MTR')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'MTR', N'Metro', N'm', 1, N'Metrico');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'CM')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'CM', N'Centímetro', N'cm', 1, N'Metrico');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'VR2')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'VR2', N'Vara cuadrada', N'vr²', 1, N'Otro');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'PIE2')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'PIE2', N'Pie cuadrado', N'ft²', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'MT2')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'MT2', N'Metro cuadrado', N'm²', 1, N'Metrico');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'GAL')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'GAL', N'Galón', N'gal', 1, N'Imperial');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'LT')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'LT', N'Litro', N'L', 1, N'Metrico');

IF NOT EXISTS (SELECT 1 FROM Inventario.UnidadesMedida WHERE Codigo = N'ML')
    INSERT INTO Inventario.UnidadesMedida (Codigo, Nombre, Simbolo, PermiteFraccion, Sistema) VALUES (N'ML', N'Mililitro', N'mL', 1, N'Metrico');
GO
