-- ============================================================================
-- Script.PostDeployment.sql — Sistemas.Repuestos.Database
--
-- Se ejecuta automáticamente después de cada Publish/Deploy de este proyecto
-- SSDT. Debe ser 100% idempotente: puede correr muchas veces sin duplicar
-- datos ni fallar si los datos ya existen.
-- ============================================================================

PRINT 'Sembrando terceros genéricos (Repuestos.Terceros)...';

IF NOT EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Nombre = N'Consumidor Final')
    INSERT INTO Repuestos.Terceros (Nombre, EsCliente)
    VALUES (N'Consumidor Final', 1);

IF NOT EXISTS (SELECT 1 FROM Repuestos.Terceros WHERE Nombre = N'Proveedor General')
    INSERT INTO Repuestos.Terceros (Nombre, EsProveedor)
    VALUES (N'Proveedor General', 1);
GO
