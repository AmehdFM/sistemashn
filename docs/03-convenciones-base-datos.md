# 03 — Convenciones de base de datos

> Este documento es el **resumen operativo y obligatorio**. La referencia
> completa, con el DDL exacto y los cuerpos de los SP no triviales, está en
> [`plan-desarrollo-base-datos.md`](../plan-desarrollo-base-datos.md).
> **Ante cualquier discrepancia, mandan los anexos de ese plan.**

---

## 1. Las nueve convenciones obligatorias (C-1 a C-9)

Aplican a **todo objeto nuevo**, en Core y en cualquier vertical. La mitad de
los defectos que se encontraron en la revisión del código existían porque
alguna de estas no estaba escrita.

**C-1 — Ningún objeto en `dbo`.** Cada área tiene su esquema propio:
`Security`, `Configuracion`, `Auditoria`, `Inventario`, `Facturacion`,
`Repuestos`. Es lo que permite que dos verticales convivan en la misma base sin
chocar.

**C-2 — La vertical nunca modifica Core.** Referencia por FK y nada más. Ni un
`ALTER TABLE` sobre `Inventario.Productos` desde `Sistemas.Repuestos.Database`.

**C-3 — Toda regla de negocio vive en el SP.** Nunca se asume que la app
validó. La app puede cambiar, ser reemplazada, o alguien puede conectarse con
SSMS.

**C-4 — Contrato de salida uniforme.** Todo SP que modifica datos devuelve como
primer result set: `Exito BIT`, `Mensaje NVARCHAR`, y sus columnas propias
(`ProductoId`, `NumeroFactura`…). Las columnas nulas van con
**`CAST(NULL AS <tipo>)` explícito**, nunca `NULL` a secas — sin el `CAST`,
Dapper recibe la columna como `int` y revienta al mapear.

**C-5 — Plantilla de transacción con soporte de anidamiento.** La regla más
importante de todas. Ver §2.

**C-6 — Validar primero, abrir transacción después.** Toda validación que pueda
hacerse sin bloquear va antes del `BEGIN TRAN`. Una transacción abierta mantiene
bloqueos; con dos cajas eso se nota.

**C-7 — Operaciones por conjunto, nunca fila por fila.** Un
`UPDATE ... FROM ... JOIN` en lugar de un cursor. La única excepción justificada
en todo el sistema es `sp_ImportarProductosMasivo`, donde el requisito explícito
es que una fila mala no tumbe el lote.

**C-8 — Todo `UPDATE ... FROM ... JOIN` contra un TVP se agrupa antes.** Si el
TVP trae el mismo `ProductoId` dos veces, el `UPDATE` aplica **una sola**
coincidencia, en silencio y sin error.

**C-9 — Todo FK lleva su índice.** SQL Server **no** crea el índice al declarar
una foreign key. Sin él, consultar o borrar por el lado padre hace scan.

## 2. La plantilla C-5, textual

Un SP puede ser llamado por la app *o* desde dentro de otro SP que ya abrió una
transacción. Un `ROLLBACK` a secas en el SP interno revierte **toda** la
transacción externa y deja al llamador haciendo `ROLLBACK` sobre algo que ya no
existe (error 3903).

```sql
CREATE PROCEDURE <Schema>.<sp_Nombre>
    @Parametros ...
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        -- 1) Validaciones de negocio con RETURN temprano, ANTES de abrir transacción.

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoSeguro;   -- punto de retorno dentro de la transacción ajena

        -- 2) Trabajo real.

        IF @TranPropia = 1 COMMIT;

        SELECT CAST(1 AS BIT) AS Exito, 'OK' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1          -- transacción condenada: solo cabe deshacer todo
            ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK;
            ELSE ROLLBACK TRANSACTION PuntoSeguro;   -- devuelve solo lo mío, la externa sigue viva
        END

        SELECT CAST(0 AS BIT) AS Exito, <mensaje amigable> AS Mensaje;
    END CATCH
END
```

**Todo SP nuevo que muta datos usa esta plantilla.** No hay excepciones.

El ejemplo de referencia completo, con validaciones previas, bloqueo de stock
dentro de la transacción y correlativo CAI, es
`Sistemas.Repuestos.Database/Repuestos/StoredProcedures/sp_RegistrarVenta.sql`.
Es el SP más delicado del sistema y el mejor modelo a copiar.

## 3. Prohibiciones absolutas

| Prohibido | Por qué |
|---|---|
| `DELAYED_DURABILITY` en cualquier forma | Cambia rendimiento por perder transacciones ya confirmadas ante un corte de luz — exactamente el escenario que hay que evitar |
| `GETUTCDATE()` / `SYSUTCDATETIME()` | No hay red ni nada con qué sincronizar. El reloj es el de la máquina: **`SYSDATETIME()` siempre** |
| SQL dinámico con concatenación | Inyección. Los parámetros van tipados |
| Cursores | Salvo `sp_ImportarProductosMasivo`, que tiene el requisito explícito de tolerar filas malas |
| Traer una tabla completa a la pantalla | 1 GB de buffer pool en Express. Todo listado va paginado en servidor |
| Dejar escapar un error crudo de SQL Server | No hay personal técnico en el sitio. `Exito`/`Mensaje` en español, detalle a auditoría |

## 4. Tipos y estilo de DDL

Tomado del DDL que ya existe. Un `CREATE TABLE` nuevo se ve así:

```sql
CREATE TABLE Inventario.Productos (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    Codigo              NVARCHAR(30)    NOT NULL,
    PrecioUnitario      DECIMAL(12,2)   NOT NULL,
    StockActual         DECIMAL(12,2)   NOT NULL DEFAULT 0,
    Activo              BIT             NOT NULL DEFAULT 1,
    FechaCreacion       DATETIME2(0)    NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_Productos_Codigo UNIQUE (Codigo),
    CONSTRAINT FK_Productos_Categorias FOREIGN KEY (CategoriaId) REFERENCES Inventario.Categorias(Id),
    CONSTRAINT CK_Productos_PrecioUnitario CHECK (PrecioUnitario >= 0)
);
GO

CREATE INDEX IX_Productos_CategoriaId ON Inventario.Productos(CategoriaId);   -- C-9
GO
```

| Elemento | Convención |
|---|---|
| Clave primaria | `Id INT IDENTITY(1,1) PRIMARY KEY` |
| Texto | `NVARCHAR(n)` siempre — nunca `VARCHAR`, hay tildes y `ñ` |
| Dinero y cantidades | `DECIMAL(12,2)` — **nunca `FLOAT` ni `MONEY`** |
| Tasas | `DECIMAL(5,2)` |
| Fecha | `DATETIME2(0)` con `DEFAULT SYSDATETIME()` |
| Booleano | `BIT NOT NULL DEFAULT 0/1` |
| Baja lógica | columna `Activo BIT` — **no se borran filas de catálogo** |
| Nombres de objeto | Tabla en plural (`Productos`), SP `sp_VerboSustantivo`, TVP `<Concepto>TableType` |
| Nombres de constraint | `PK_`, `UQ_`, `FK_<Tabla>_<Referida>`, `CK_<Tabla>_<Columna>`, `IX_<Tabla>_<Columnas>` |
| Literales de texto | siempre con prefijo `N`: `N'Administrador'` |

Cada archivo `.sql` contiene **un solo objeto** y vive en la carpeta de su
esquema y tipo: `<Esquema>/Tables/`, `<Esquema>/StoredProcedures/`,
`<Esquema>/Types/`, `<Esquema>/Functions/`, `<Esquema>/Sequences/`.
Todo archivo nuevo debe registrarse en el `.sqlproj` correspondiente.

## 5. Índices

No se crea un índice "por si acaso": en Express cada índice es RAM que no sobra
y escrituras más lentas. Reglas:

1. **Todo FK lleva índice** (C-9). Ese es el único caso automático.
2. **Los demás se diseñan para cubrir una consulta concreta**, con `INCLUDE`
   para evitar el key lookup.
3. **Un índice sobre un `BIT` con distribución desbalanceada no sirve.** Un
   índice sobre `Activo` cuando el 95 % está activo no aporta selectividad y el
   optimizador hace scan igual. La solución es un **índice filtrado** que cubra
   la consulta real:

```sql
CREATE INDEX IX_Productos_Activo_Nombre
    ON Inventario.Productos(Nombre)
    INCLUDE (Codigo, PrecioUnitario, StockActual, StockMinimo, CategoriaId, TasaISV, UnidadMedidaId)
    WHERE Activo = 1;
```

## 6. Script de post-despliegue

`Script.PostDeployment.sql` corre después de cada `Publish` y **debe ser 100 %
idempotente**: puede ejecutarse muchas veces sin duplicar datos ni fallar.
El patrón es siempre `IF NOT EXISTS (...) INSERT ...`.

Siembra hoy: roles base (`Administrador`, `Usuario`) y unidades de medida.
`Inventario.UnidadesMedida` fuerza `Id = 1` para "Unidad" con
`SET IDENTITY_INSERT`, porque `Productos.UnidadMedidaId` usa `DEFAULT 1` como
literal.

## 7. Auditoría

`Auditoria.Auditoria` es la única tabla del sistema que crece sin techo, y la
base tiene un límite duro de 10 GB en Express. **Necesita purga por antigüedad
desde el día uno**, no cuando el cliente llame porque el sistema dejó de
guardar. Se registra vía `Auditoria.sp_RegistrarAuditoria` y se purga con
`Auditoria.sp_PurgarAuditoria`.

Cuando un SP falla por una condición técnica, el detalle va a auditoría con un
código de referencia; al usuario le llega un mensaje en español y ese código,
para que soporte pueda pedirlo por teléfono.

## 8. Colación y compatibilidad — decisiones abiertas

El `.sqlproj` declara hoy `ModelCollation` = `1033, CI` (acento-**sensitiva**)
y `DSP` = `Sql170` (SQL Server 2022). Ambas cosas están **pendientes de
decisión del negocio** y no se cambian por cuenta propia:

- [ADR-0016 — Collation acento-insensitiva](decisiones/ADR-0016-collation-acento-insensitiva.md)
  · **debe resolverse antes de la primera instalación con datos reales**
- [ADR-0021 — Versión mínima de SQL Server](decisiones/ADR-0021-version-minima-de-sql-server.md)

## 9. Checklist antes de dar por terminado un objeto SQL

- [ ] Está en su esquema propio, nunca en `dbo` (C-1)
- [ ] Si es de una vertical, no toca Core más que por FK (C-2)
- [ ] La regla de negocio está en el SP, no asumida desde la app (C-3)
- [ ] Devuelve `Exito`/`Mensaje` con `CAST(NULL AS <tipo>)` en las nulas (C-4)
- [ ] Usa la plantilla C-5 completa si muta datos
- [ ] Las validaciones que no bloquean van antes del `BEGIN TRAN` (C-6)
- [ ] Nada de cursores (C-7)
- [ ] Los `UPDATE` contra TVP agrupan antes (C-8)
- [ ] Cada FK tiene su índice (C-9)
- [ ] `SYSDATETIME()`, `NVARCHAR`, `DECIMAL(12,2)`, literales con `N'...'`
- [ ] Si es listado, está paginado en servidor
- [ ] El archivo está registrado en el `.sqlproj`
- [ ] Los mensajes al usuario están en español y no revelan detalle técnico
