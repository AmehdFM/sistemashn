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
