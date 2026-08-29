# Plan de desarrollo — Sistemas.Core.Database

## Contexto del proyecto

Este es el proyecto de base de datos compartido (`SQL Server Database Project`, SSDT) dentro de la solución `SistemasHN`. Contiene las tablas y procedimientos almacenados **comunes a todas las verticales** (Ferretería, RH, Repuestos, Taller, Carwash) que se van a construir sobre este Core. Motor: **SQL Server 2025 Express**. Cada vertical tendrá su propio proyecto `.Database` con una referencia "misma base de datos" hacia este, así que todo lo que se construya acá debe ser genérico — nada específico de un rubro.

## Regla central

Toda regla de negocio vive en procedimientos almacenados, no en la capa visual (.NET). Los SPs deben:
- Validar internamente lo que necesiten validar (no asumir que la app ya validó).
- Envolver en transacción (`BEGIN TRAN` / `COMMIT` / `ROLLBACK` en `TRY/CATCH`) cualquier operación que toque más de una tabla.
- Devolver un resultado claro (`Exito BIT`, `Mensaje NVARCHAR`, datos relevantes) — nunca dejar que una excepción cruda llegue a la app.
- Usar `WITH ENCRYPTION` como capa mínima adicional.

## Organización por schema (no usar `dbo`)

Cada módulo tiene su propio schema de SQL Server. Esto es obligatorio, no solo organización de carpetas — evita choques de nombres cuando las verticales se combinen entre sí más adelante.

---

## Módulos a construir, en este orden

### 1. `Security` (primero — todo lo demás depende de login/usuarios)
**Tablas:**
- `Security.Usuarios` — usuario, contraseña (hash), rol, activo/inactivo
- `Security.Roles` — nombre de rol, permisos asociados

**SPs:**
- `Security.sp_Login` — valida credenciales, devuelve rol/permisos

**Criterio de terminado:** un usuario puede autenticarse y el SP devuelve su rol correctamente; contraseñas nunca se guardan en texto plano.

---

### 2. `Configuracion`
**Tablas:**
- `Configuracion.Configuracion` — nombre comercial, RTN, dirección, teléfono, logo (una fila por instalación)

**SPs:**
- `Configuracion.sp_GuardarConfiguracion`

**Criterio de terminado:** se puede leer y actualizar la configuración general sin duplicar filas.

---

### 3. `Auditoria`
**Tablas:**
- `Auditoria.Auditoria` — usuario, operación, tabla afectada, fecha, detalle

**SPs:**
- `Auditoria.sp_RegistrarAuditoria` — pensado para ser llamado desde otros SPs (de Core o de cada vertical)

**Criterio de terminado:** cualquier otro SP (de Core o futuro de una vertical) puede llamarlo pasando usuario + operación + detalle, sin fallar si falta algún dato opcional.

---

### 4. `Inventario`
**Tablas:**
- `Inventario.Productos` — Id, Codigo, Nombre, Descripcion, PrecioUnitario, CategoriaId (FK), Activo. Solo campos genéricos — nada específico de un rubro (eso se extiende desde cada vertical con FK hacia acá).
- `Inventario.Categorias` — Id, Nombre, CategoriaPadreId (jerárquico)
- `Inventario.Etiquetas` — Id, Nombre
- `Inventario.ProductoEtiqueta` — tabla puente N:N

**SPs:**
- `Inventario.sp_CrearProducto`, `sp_ListarProductos`, `sp_CrearCategoria`, `sp_AsignarEtiqueta`
- `Inventario.sp_ImportarProductosMasivo` — usa un **Table-Valued Parameter** (`Inventario.ProductoTableType`) + `MERGE`, para que cualquier vertical pueda importar/actualizar productos masivamente desde Excel en una sola transacción (ver ejemplo abajo)

```sql
CREATE TYPE Inventario.ProductoTableType AS TABLE (
    Codigo NVARCHAR(30),
    Nombre NVARCHAR(150),
    PrecioUnitario DECIMAL(12,2),
    CategoriaId INT
);

CREATE PROCEDURE Inventario.sp_ImportarProductosMasivo
    @Productos Inventario.ProductoTableType READONLY
AS
BEGIN
    MERGE Inventario.Productos AS destino
    USING @Productos AS origen
    ON destino.Codigo = origen.Codigo
    WHEN MATCHED THEN
        UPDATE SET Nombre = origen.Nombre, PrecioUnitario = origen.PrecioUnitario, CategoriaId = origen.CategoriaId
    WHEN NOT MATCHED THEN
        INSERT (Codigo, Nombre, PrecioUnitario, CategoriaId)
        VALUES (origen.Codigo, origen.Nombre, origen.PrecioUnitario, origen.CategoriaId);
END
```

**Criterio de terminado:** una vertical puede crear un producto simple sin campos extra, y puede importar un lote de 500+ productos en una sola llamada sin que una fila con error tumbe todo el lote (definir cómo se reportan errores por fila — a resolver junto al desarrollador de .NET).

---

### 5. `Facturacion`
**Tablas:**
- `Facturacion.ConfiguracionCAI` — rango autorizado, correlativo actual, fecha de vencimiento

**Functions:**
- `Facturacion.fn_CalcularISV` — aplica 15%/18%/exento sobre un monto

**SPs:**
- `Facturacion.sp_ObtenerCorrelativoCAI` — valida vigencia y rango, incrementa el correlativo **de forma atómica** (crítico: dos ventas simultáneas nunca deben recibir el mismo número)

**Criterio de terminado:** llamadas concurrentes a `sp_ObtenerCorrelativoCAI` (probarlo con al menos 2 sesiones simultáneas) nunca devuelven el mismo correlativo; el SP rechaza claramente si el CAI está vencido o fuera de rango.

---

## Fuera de alcance de este proyecto (no construir acá)

- Ninguna tabla de "Venta" (encabezado/detalle) — eso es específico de cada vertical.
- Ningún cálculo de negocio propio de un rubro (nómina, diagnóstico de taller, etc.).
- Ningún dato con campos que solo apliquen a un rubro — si algo tienta a agregar un campo "por si acaso" pensando en un rubro específico, no va acá.

## Checklist general antes de dar por cerrado el proyecto

- [ ] Todos los objetos usan su schema correspondiente, nada quedó en `dbo`
- [ ] Todas las tablas tienen las constraints necesarias (`FK`, `CHECK`, `NOT NULL`) — no se delega esa validación solo al SP
- [ ] Todo SP que toca más de una tabla usa transacción con rollback
- [ ] Todo SP devuelve resultado claro de éxito/error
- [ ] El proyecto compila sin errores (`.dacpac` se genera correctamente)
- [ ] Se probó `sp_ObtenerCorrelativoCAI` con concurrencia
- [ ] Se probó `sp_ImportarProductosMasivo` con un lote grande (500+ filas)
