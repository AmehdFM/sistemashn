# Plan de desarrollo — Base de datos y lógica de negocio

**Alcance de este documento:** todo lo que vive dentro de SQL Server — DDL, stored procedures, índices, transacciones, despliegue y respaldo. La capa .NET aparece únicamente cuando el contrato entre ambas define una regla (por ejemplo, quién verifica la contraseña). Nada de Forms, Services ni DTOs.

**Este documento reemplaza** a `plan-desarrollo-core-database.md` y a `Sistemas.Repuestos.Database/plan-desarrollo-repuestos-detallado.md`, ambos eliminados. El diseño de aquellos se conserva aquí, corregido donde la revisión encontró problemas.

**Estado al momento de escribirlo:** Core está construido y funcional salvo los defectos de la sección 3. La vertical Repuestos son 15 archivos `.sql` de 0 bytes.

---

## 0. Cómo usar este documento para implementar

Este documento está pensado para que alguien —persona o IA en una sesión nueva, sin contexto previo— pueda construir todo sin inventar nada. Si estás en esa situación, seguí este orden:

1. **Leé primero el código que ya existe** en `Sistemas.Core.Database/`. Las tablas y SPs de Core están implementados y son la referencia de estilo. No los reescribas salvo donde la sección 4 lo indica.
2. **Leé las secciones 1 a 3** para entender por qué el diseño es como es y qué está roto hoy.
3. **Ejecutá la Fase 0** (sección 4) completa antes de tocar la vertical.
4. **Construí las fases 1 a 6** (sección 5) en orden. Las secciones 5.x explican el *por qué* de cada decisión; el **Anexo A** tiene el DDL exacto y el **Anexo B** los cuerpos de los SP no triviales. Ante cualquier discrepancia, **manda el anexo**.
5. **El Anexo C** lista archivo por archivo qué crear y su entrada en el `.sqlproj`.

**Reglas para quien implemente:**
- Las convenciones de la sección 2 son obligatorias, en especial la plantilla **C-5** de transacción anidada. Todo SP nuevo la usa.
- Las decisiones de la sección 10 (`D-1` a `D-6`) **no se resuelven por cuenta propia**. Donde el anexo asume una, lo dice explícitamente.
- Si algo del anexo no compila contra el modelo real, priorizá lo que el modelo dice y reportalo — el anexo se escribió contra el código revisado, no contra un despliegue verificado.

---

## 1. El entorno manda el diseño

Estas no son preferencias de estilo. Cada restricción del mercado al que va dirigido el producto obliga a una decisión técnica concreta, y el resto del documento se apoya en ellas.

| Restricción real | Consecuencia obligatoria en la base de datos |
|---|---|
| **Sin internet** | Cero dependencias externas. Nada de llamadas HTTP desde SQL, ni sincronización, ni validación de licencia en línea desde la BD. El reloj es el de la máquina: se usa `SYSDATETIME()` de forma consistente, nunca `GETUTCDATE()`, porque no hay a qué sincronizar. |
| **Cortes de energía repentinos** | La durabilidad de la transacción es innegociable. **Prohibido `DELAYED_DURABILITY`** en cualquier forma: cambia rendimiento por perder transacciones ya confirmadas ante un corte, que es exactamente el escenario a evitar. Toda operación de dinero o inventario es una sola transacción atómica. El respaldo automático deja de ser una comodidad y pasa a ser parte del producto. |
| **PC de bajos recursos** | SQL Server Express solo usa **1 GB de buffer pool** y hasta 4 cores de un socket. Nada de traer tablas completas a la pantalla: toda consulta de listado va paginada en el servidor. Los índices se diseñan para cubrir la consulta, no "por si acaso" — cada índice extra es RAM que no sobra y escrituras más lentas. |
| **Base de datos de 10 GB máximo (Express)** | `Auditoria.Auditoria` crece sin techo y es la única tabla con ese perfil. Necesita purga por antigüedad desde el día uno, no cuando el cliente llame porque el sistema dejó de guardar. |
| **Sin personal técnico en el sitio** | Ningún SP puede dejar escapar un error crudo de SQL Server a la pantalla. Todo SP devuelve `Exito`/`Mensaje` en español. Los detalles técnicos van a auditoría con un código de referencia que el soporte pueda pedir por teléfono. |
| **Se vende a muchos clientes, cada uno con su copia** | Hace falta versionado de esquema y actualización por DACPAC. Sin eso, actualizar 30 instalaciones offline es inviable. |
| **Español de Honduras** | La collation actual del proyecto (`1033, CI`) es **acento-sensitiva**: buscar `cigueñal` no encuentra `cigüeñal`, y `bujia` no encuentra `bujía`. Ver la decisión D-1. |

---

## 2. Convenciones obligatorias

Estas reglas aplican a todo objeto nuevo, en Core y en cualquier vertical. La mitad de los defectos de la sección 3 existen porque alguna de estas no estaba escrita.

**C-1 — Ningún objeto en `dbo`.** Cada schema es propio (`Security`, `Configuracion`, `Auditoria`, `Inventario`, `Facturacion`, `Repuestos`). Es lo que permite que dos verticales convivan en la misma base sin chocar.

**C-2 — La vertical nunca modifica Core.** Referencia por FK, nada más. Ni un `ALTER TABLE` sobre `Inventario.Productos` desde `Sistemas.Repuestos.Database`.

**C-3 — Toda regla de negocio vive en el SP.** Nunca se asume que la app validó. La app puede cambiar, ser reemplazada, o alguien puede conectarse con SSMS.

**C-4 — Contrato de salida uniforme.** Todo SP que modifica datos devuelve como primer result set: `Exito BIT`, `Mensaje NVARCHAR`, y las columnas de salida propias (`ProductoId`, `NumeroFactura`, etc.). Las columnas nulas van con `CAST(NULL AS <tipo>)` explícito, nunca `NULL` a secas — sin el `CAST`, Dapper recibe la columna como `int` y revienta al mapear.

**C-5 — Plantilla de transacción con soporte de anidamiento.** Esta es la regla nueva más importante. Un SP puede ser llamado directamente por la app *o* desde dentro de otro SP que ya abrió una transacción. Un `ROLLBACK` a secas en el SP interno revierte **toda** la transacción externa y deja al SP llamador haciendo `ROLLBACK` sobre algo que ya no existe (error 3903). La plantilla obligatoria:

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

**C-6 — Validar primero, abrir transacción después.** Toda validación que pueda hacerse sin bloquear va antes del `BEGIN TRAN`. Una transacción abierta mantiene bloqueos; en una caja con dos terminales eso se nota.

**C-7 — Operaciones por conjunto, nunca fila por fila.** Un `UPDATE ... FROM ... JOIN` en lugar de un cursor. La única excepción justificada en todo el sistema es `sp_ImportarProductosMasivo`, donde el requisito explícito es que una fila mala no tumbe el lote.

**C-8 — Todo `UPDATE ... FROM ... JOIN` contra un TVP se agrupa antes.** Ver defecto B-4: si el TVP trae el mismo `ProductoId` dos veces, el `UPDATE` aplica **una sola** de las coincidencias en silencio.

**C-9 — Todo FK lleva su índice.** SQL Server **no** crea índice al declarar una foreign key. Sin él, borrar o consultar por el lado padre hace scan.

---

## 3. Hallazgos de la revisión del código actual

Ordenados por lo que rompe primero.

### A. Bloqueantes de compilación

**A-1 — `Sistemas.Core.Database` no compila: faltan dos tablas en el proyecto.**
`Sistemas.Core.Database.sqlproj` no incluye `Security\Tables\Roles.sql` ni `Security\Tables\Usuarios.sql` en el `ItemGroup` de `Build`. Los archivos existen en disco pero están fuera del modelo, así que el FK de `Auditoria.Auditoria` y todos los SPs de `Security` referencian objetos que SSDT no conoce.
→ Agregar ambas entradas al `.sqlproj`.

**A-2 — `Sistemas.Repuestos.Database.sqlproj` apunta a rutas inexistentes.**
El `ItemGroup` agregado lista 17 archivos en la raíz (`DetalleProducto.sql`) cuando viven en `Repuestos/Tables/`. Además incluye `DetalleProducto.sql`, que está borrado del working tree.
→ Reescribir el `ItemGroup` con las rutas reales, incluir los archivos que faltan (sección 5) y recrear `DetalleProducto.sql`.

**A-3 — Archivos fuera de lugar y faltantes en Repuestos.**
`Compras.sql` está en `Repuestos/Compras/` en vez de `Repuestos/Tables/`. No existen `CompraDetalle.sql`, `CuentasPorPagar.sql`, `PagoCuentaPorCobrar.sql`, `PagoCuentaPorPagar.sql`, ni los tipos `PaqueteDetalleTableType` y `VentaDetalleTableType`.

**A-4 — `core.zip` está versionado en git y `Repuestos.zip` sin versionar.**
Respaldos manuales dentro del repo. Agregar `*.zip` al `.gitignore` y sacar `core.zip` del control de versiones (`git rm --cached`).

### B. Defectos funcionales

**B-1 — `Security.sp_Login` está roto y debe eliminarse.**
Compara `@PasswordHash <> @StoredPasswordHash` por igualdad literal. BCrypt genera un salt aleatorio distinto en cada hash, así que dos hashes de la misma contraseña **nunca** son iguales: con este SP nadie inicia sesión jamás. Ya fue reemplazado correctamente por `sp_ObtenerCredencialesLogin` + `sp_RegistrarResultadoLogin`, pero sigue en el proyecto y compilando, listo para que alguien lo llame por error.
→ Borrar el archivo y su entrada del `.sqlproj`.

**B-2 — `Configuracion.Configuracion` falla en producción con un usuario de aplicación.**
La columna `Id` es `IDENTITY(1,1)` y a la vez tiene `CHECK (Id = 1)`. Para insertar la fila 1, `sp_GuardarConfiguracion` recurre a `SET IDENTITY_INSERT ... ON`, que exige permiso **`ALTER` sobre la tabla**. Un usuario de aplicación con solo `EXECUTE` sobre los SPs — que es como debe desplegarse — no lo tiene, y el primer guardado de configuración revienta.
→ Quitar `IDENTITY` de la columna. Es un singleton, no necesita generar identidades: `Id INT NOT NULL CONSTRAINT PK_Configuracion PRIMARY KEY CONSTRAINT CK_Configuracion_Singleton CHECK (Id = 1)`, e insertar el literal `1`.

**B-3 — `sp_ObtenerCorrelativoCAI` corrompe la transacción de quien lo llama.**
Este es el defecto más serio del sistema, y se activa justo en la operación más importante. El SP abre su propia transacción y hace `ROLLBACK` completo en los tres caminos de error (CAI ausente, vencido, agotado). Pero `sp_RegistrarVenta` lo invoca **dentro** de su propia transacción abierta. Consecuencias encadenadas:

- El `COMMIT` interno no confirma nada; solo decrementa `@@TRANCOUNT`.
- Cualquiera de los tres `ROLLBACK` internos **revierte la transacción completa de la venta**, no solo la parte del CAI.
- Tras ese rollback, `sp_RegistrarVenta` sigue ejecutando y llega a su propio `ROLLBACK`, que falla con error 3903 porque ya no hay transacción. El cajero ve un error incomprensible en lugar de "el CAI está vencido".

→ Reescribir siguiendo la plantilla C-5. Los caminos de error devuelven `Exito = 0` **sin** hacer `ROLLBACK` de la transacción ajena; el SP llamador decide.

**B-4 — `sp_RegistrarCompra` pierde stock silenciosamente con productos repetidos.**
El incremento se hace con `UPDATE p SET p.StockActual = p.StockActual + d.Cantidad FROM Inventario.Productos p INNER JOIN @Detalle d ON d.ProductoId = p.Id`. Cuando el TVP trae el mismo `ProductoId` en dos líneas — el caso normal de "me llegaron 10 filtros en una caja y 5 en otra" — el `UPDATE ... FROM` aplica **una sola** de las coincidencias, sin error ni advertencia. Se compran 15, entran 10. El `CompraDetalle` sí guarda las dos líneas, así que el inventario y el documento quedan en desacuerdo y nadie se entera hasta el conteo físico.
→ Agrupar antes: `INNER JOIN (SELECT ProductoId, SUM(Cantidad) AS Cantidad FROM @Detalle GROUP BY ProductoId) d`. `sp_RegistrarVenta` ya lo hace bien con `@StockRequerido`; la compra quedó sin ese cuidado.

**B-5 — El chequeo de stock de `sp_RegistrarVenta` es una condición de carrera.**
La validación ocurre fuera de la transacción (decisión correcta: evita quemar un correlativo en una venta que iba a fallar). Pero con dos terminales, ambas pueden validar contra el mismo stock de 5 y ambas entrar. La segunda choca contra `CHECK (StockActual >= 0)` **dentro** de la transacción y el cajero recibe una violación de constraint en crudo.
→ Mantener la validación previa como filtro rápido, y **re-validar dentro de la transacción** leyendo con `WITH (UPDLOCK)`. Ahí sí devolver "Stock insuficiente" de forma controlada.

**B-6 — `sp_RegistrarVenta` no verifica que el producto exista ni esté activo.**
Un `ProductoId` inexistente en el TVP se cae del `INNER JOIN` del cálculo de montos y desaparece del subtotal, pero el FK de `VentaDetalle` lo rechaza después, ya dentro de la transacción. Y un producto con `Activo = 0` (descontinuado) se vende sin objeción.
→ Validar existencia y `Activo = 1` de todos los `ProductoId` del TVP antes de abrir la transacción, con mensaje que nombre el código problemático.

**B-7 — `sp_AnularVenta` restaura stock usando la composición actual del paquete.**
Expande `PaqueteDetalle` en el momento de la anulación. Si el paquete se rearmó entre la venta y la anulación —`sp_ArmarPaquete` borra y reinserta el detalle—, se devuelve al inventario un conjunto de componentes distinto al que salió. El inventario queda mal sin ningún error visible.
→ `VentaDetalle` debe guardar las líneas **ya expandidas** además de la línea comercial del paquete, o bien versionar la composición. Ver decisión D-3.

**B-8 — `sp_AnularVenta` no toca la cuenta por cobrar.**
Anular una venta a crédito deja la fila de `CuentasPorCobrar` viva con su saldo. La tienda sigue cobrando una factura anulada. Requiere decisión de negocio (D-4), pero el estado actual —ignorarlo— no es una opción válida.

**B-9 — La auditoría sí puede tumbar la operación que la llamó.**
`sp_RegistrarAuditoria` envuelve su `INSERT` en `TRY/CATCH` con la intención documentada de "nunca fallar la operación principal". No funciona: los SPs que la invocan tienen `SET XACT_ABORT ON`, y bajo esa opción un error de escritura deja la transacción **condenada** (`XACT_STATE() = -1`). El `CATCH` interno atrapa el error y hace `PRINT`, pero la transacción ya no puede confirmarse, y el `COMMIT` del SP llamador falla. Una venta perfecta se pierde porque no se pudo escribir su renglón de auditoría.
→ Ver sección 4, tarea 4.6.

**B-10 — Un ciclo de categorías de más de un nivel es posible.**
`CK_Categorias_NoAutoReferencia CHECK (CategoriaPadreId <> Id)` bloquea A→A pero no A→B→A. Un `CHECK` no puede recorrer la jerarquía.
→ Validar en `sp_CrearCategoria` / el futuro `sp_ActualizarCategoria` con un CTE recursivo antes de asignar el padre.

### C. Rendimiento

**C-1 — `sp_ListarProductos` es un scan completo y trae todo.**
Tres problemas superpuestos, y es la consulta más frecuente del sistema:
- `LIKE '%' + @Busqueda + '%'` con comodín inicial no puede usar índice. Scan de toda la tabla en cada tecla.
- Sin paginación: con 20 000 productos, cada búsqueda cruza 20 000 filas por la red local y las materializa en la grilla. En una PC de 4 GB eso es la diferencia entre instantáneo y tres segundos.
- El `WHERE` con parámetros opcionales encadenados por `OR` genera un plan único cacheado que sirve mal a los demás casos (*parameter sniffing*).

→ Agregar `@Pagina INT = 1`, `@TamanoPagina INT = 50` con `OFFSET ... FETCH NEXT`; devolver el total en un segundo result set; cerrar con `OPTION (RECOMPILE)` — es una consulta interactiva, recompilar cuesta menos que ejecutar un plan malo. Para la búsqueda, ver D-2.

**C-2 — Los índices de `Inventario.Productos` no cubren el caso de uso.**
`IX_Productos_Activo` sobre una columna `BIT` tiene selectividad casi nula: el 95 % de los productos están activos, y el optimizador prefiere el scan de todos modos. No existe índice sobre `Nombre`, que es por donde se busca.
→ Reemplazar por un índice filtrado que cubra la consulta real:
```sql
CREATE INDEX IX_Productos_Activo_Nombre
    ON Inventario.Productos(Nombre)
    INCLUDE (Codigo, PrecioUnitario, StockActual, StockMinimo, CategoriaId, TasaISV)
    WHERE Activo = 1;
```

**C-3 — Faltan los índices de las foreign keys.** Aplica a `VentaDetalle.VentaId`, `CompraDetalle.CompraId`, `PaqueteDetalle.PaqueteId`, `VehiculoCompatible.ProductoId`, `PagoCuentaPorCobrar.CuentaPorCobrarId`, `PagoCuentaPorPagar.CuentaPorPagarId`. Sin ellos, abrir el detalle de una factura hace scan de todos los detalles de la historia.

**C-4 — `Ventas` necesita índice por fecha.** El corte diario y el arqueo de caja filtran por `Fecha`. Índice filtrado por `Anulada = 0`, que es como siempre se consulta.

**C-5 — `fn_CalcularISV` es una UDF escalar sin `SCHEMABINDING`.**
Se invoca dentro de un `SUM()` sobre un conjunto en `sp_RegistrarVenta`. Las UDF escalares se ejecutan una vez por fila y bloquean el paralelismo salvo que el optimizador logre *inlinearlas*, lo que exige nivel de compatibilidad 150+ y que la función califique.
→ Agregar `WITH SCHEMABINDING`, verificar con el plan de ejecución que se inlinea, y si no, escribir la aritmética directamente en el SP. Con facturas de 5 líneas la diferencia es irrelevante; el punto es no dejar el patrón instalado para cuando aparezca un reporte que la llame un millón de veces.

**C-6 — `Configuracion.Logo VARBINARY(MAX)` vive en la tabla de configuración.**
Cada lectura de la configuración arrastra la imagen. Con 1 GB de buffer pool, no es gratis.
→ Ningún SP debe hacer `SELECT *` sobre esa tabla; el logo se lee con un SP dedicado que se llama solo al imprimir.

### D. Robustez y operación

**D-1 — `Auditoria.Auditoria` no tiene purga.** Es la única tabla de crecimiento ilimitado y el límite de Express es 10 GB para toda la base. Sin purga, el sistema deja de aceptar ventas por una tabla de bitácora.

**D-2 — No existe versionado de esquema.** Al vender a N clientes con instalaciones offline, no hay forma de saber en qué versión está cada uno ni de aplicar actualizaciones de forma segura.

**D-3 — El respaldo no existe.** `Sistemas.Mantenimiento` (`BackupService`, `ClearService`) son clases vacías de 10 líneas. En el contexto descrito — cortes de energía, sin técnico en sitio — esto es el riesgo operativo número uno del producto.

**D-4 — Falta bloqueo por intentos fallidos de login.** `sp_ObtenerCredencialesLogin` devuelve el hash sin límite de intentos. Aceptable en una red aislada, pero barato de agregar y esperable en un sistema que se vende.

**D-5 — El `.sqlproj` apunta a SQL Server 2022, el plan original decía 2025.** El DSP es `Sql170DatabaseSchemaProvider`. No es un error, pero hay que fijarlo conscientemente: apuntar a la versión más baja que se vaya a instalar en un cliente, no a la más alta.

---

## 4. Fase 0 — Dejar Core sano

Nada de la vertical se puede probar hasta que Core compile y sea correcto. Cada tarea corresponde a un hallazgo de la sección 3.

| # | Tarea | Resuelve |
|---|---|---|
| 4.1 | Agregar `Security\Tables\Roles.sql` y `Usuarios.sql` al `ItemGroup` de `Build` del `.sqlproj` | A-1 |
| 4.2 | Borrar `Security/StoredProcedures/sp_Login.sql` y su entrada del `.sqlproj` | B-1 |
| 4.3 | Quitar `IDENTITY` de `Configuracion.Configuracion.Id`; eliminar el `SET IDENTITY_INSERT` de `sp_GuardarConfiguracion` e insertar el literal `1` | B-2 |
| 4.4 | Reescribir `sp_ObtenerCorrelativoCAI` con la plantilla C-5 (savepoint, sin `ROLLBACK` de transacción ajena) | B-3 |
| 4.5 | Agregar `WITH SCHEMABINDING` a `fn_CalcularISV` y confirmar el inlining en el plan | C-5 |
| 4.6 | Resolver el acoplamiento auditoría/transacción | B-9 |
| 4.7 | Reescribir `sp_ListarProductos` con paginación `OFFSET/FETCH`, conteo total en segundo result set y `OPTION (RECOMPILE)` | C-1 |
| 4.8 | Reemplazar `IX_Productos_Activo` por el índice filtrado con `INCLUDE` | C-2 |
| 4.9 | Validación anti-ciclo con CTE recursivo en `sp_CrearCategoria` | B-10 |
| 4.10 | `Configuracion.sp_ObtenerLogo` dedicado; sacar `Logo` de toda otra consulta | C-6 |
| 4.11 | `Auditoria.sp_PurgarAuditoria` + tabla de versión de esquema | D-1, D-2 |
| 4.12 | Sacar `core.zip` de git y agregar `*.zip` al `.gitignore` | A-4 |

**Detalle de 4.6 — auditoría que no puede tumbar la operación.**
Tres opciones, en orden de preferencia:

1. **Auditar fuera de la transacción de negocio** (recomendada). El SP acumula lo que va a auditar en una variable y llama a `sp_RegistrarAuditoria` **después** del `COMMIT`. Si falla, ya no hay nada que condenar: la venta está guardada. Cuesta que un fallo de auditoría deje la operación sin registro, que es exactamente el intercambio que el diseño original quería y no lograba.
2. Escribir la auditoría con `INSERT` en una tabla sin constraints ni FK, para que la probabilidad de fallo tienda a cero. Complementa a la opción 1, no la sustituye.
3. Auditar en una sesión aparte con `sp_executesql` fuera del contexto transaccional. Más frágil; no recomendado.

Elegir la 1 y aplicarla a todos los SPs que hoy auditan dentro de la transacción: `sp_CrearProducto`, `sp_CrearCategoria`, `sp_AsignarEtiqueta`, `sp_GuardarConfiguracion`, y todos los de Repuestos.

**Detalle de 4.11 — purga y versión.**

```sql
CREATE PROCEDURE Auditoria.sp_PurgarAuditoria
    @DiasAConservar INT = 365
AS
```
Borra en lotes de 5 000 filas dentro de un `WHILE` con `WAITFOR DELAY '00:00:00.100'` entre lotes. Un `DELETE` masivo de una tabla de millones de filas escala el bloqueo a nivel de tabla y congela el sistema; en lotes, cada transacción es corta y otras sesiones siguen trabajando. Lo dispara `Sistemas.Mantenimiento`, no un job del Agent — **SQL Server Express no incluye SQL Server Agent**, dato que condiciona todo el diseño de mantenimiento.

```sql
CREATE TABLE Configuracion.VersionEsquema (
    Id              INT IDENTITY(1,1) PRIMARY KEY,
    Version         NVARCHAR(20)  NOT NULL,   -- '1.0.0'
    Vertical        NVARCHAR(50)  NOT NULL,   -- 'Core' | 'Repuestos'
    FechaAplicacion DATETIME2(0)  NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT UQ_VersionEsquema UNIQUE (Vertical, Version)
);
```

---

## 5. Fase 1 a 6 — Construcción de la vertical Repuestos

Orden obligatorio: cada fase depende de la anterior. Todo objeto va en el schema `Repuestos` y aplica las convenciones de la sección 2.

### Fase 1 — Extensión de catálogo

**Archivos:** `Repuestos/Tables/DetalleProducto.sql` (recrear), `VehiculoCompatible.sql`, `NumeroEquivalente.sql`.

`DetalleProducto` es una extensión **1:1 opcional** de `Inventario.Productos`: `ProductoId` como PK y FK a la vez, más `NumeroParte NVARCHAR(50) NULL`, `MarcaFabricante NVARCHAR(50) NULL`, `EsOriginal BIT NOT NULL DEFAULT 1`. Opcional porque un insumo genérico —grasa, trapos— no tiene número de parte. Toda consulta la ataca con `LEFT JOIN`, nunca `INNER`.

`VehiculoCompatible` es 1:N con `Marca`, `Modelo`, `AnioDesde`/`AnioHasta SMALLINT`, `CHECK (AnioHasta >= AnioDesde)` y `UNIQUE (ProductoId, Marca, Modelo, AnioDesde, AnioHasta)`. Índice sobre `(Marca, Modelo)` porque la consulta real es "¿qué tengo para un Corolla 2015?".

> **Corrección respecto al plan anterior:** aquel definía `CHECK (AnioDesde BETWEEN 1950 AND YEAR(GETDATE()) + 1)`. **`GETDATE()` no es determinística y no se admite en un `CHECK`** — SSDT lo rechaza al compilar. El límite superior se valida en el SP de alta, no en la tabla.

`NumeroEquivalente` es 1:N con `NumeroOEM NVARCHAR(50) NOT NULL`, `Fabricante NVARCHAR(50) NULL`, `UNIQUE (ProductoId, NumeroOEM)` e **índice dedicado sobre `NumeroOEM`**: el caso de uso central del rubro es "el cliente trae un número de otro fabricante, ¿qué tengo que sirva?", y esa búsqueda tiene que ser instantánea.

**SPs:** `sp_GuardarDetalleProducto` (upsert de la fila 1:1), `sp_AgregarVehiculoCompatible`, `sp_AgregarNumeroEquivalente`, `sp_BuscarPorEquivalencia` — este último recibe un número y devuelve los productos que lo listan como equivalente **o** cuyo `NumeroParte` coincide, unificados y paginados.

### Fase 2 — Proveedores

**Archivos:** `Proveedores.sql`, `ProductoProveedor.sql`.

`Proveedores` con `UNIQUE (Nombre)` y RTN opcional validado con el mismo formato de 14 dígitos que Core: `CHECK (RTN IS NULL OR (LEN(RTN) = 14 AND RTN NOT LIKE '%[^0-9]%'))`. `ProductoProveedor` con PK compuesta `(ProductoId, ProveedorId)` y `PrecioCompra DECIMAL(12,2) CHECK (>= 0)`.

**SPs:** `sp_GuardarProveedor`, `sp_ListarProveedores` (paginado), `sp_GuardarPrecioProveedor` (upsert), `sp_CompararPreciosProveedor` — dado un `ProductoId`, lista los proveedores ordenados por precio. Es la consulta que le ahorra dinero al dueño y la razón de existir del módulo.

### Fase 3 — Compras

**Archivos:** `Compras.sql` (mover desde `Repuestos/Compras/`), `CompraDetalle.sql`, `Types/CompraDetalleTableType.sql`, `StoredProcedures/sp_RegistrarCompra.sql`.

`Compras`: `ProveedorId`, `NumeroFacturaProveedor NVARCHAR(30) NULL`, `Fecha`, `Total`, `UsuarioId`, `EsCredito`. `CompraDetalle`: `CompraId`, `ProductoId`, `Cantidad CHECK (> 0)`, `CostoUnitario CHECK (>= 0)`, y `Subtotal AS (Cantidad * CostoUnitario) PERSISTED` — calculada y persistida, para que un `INSERT` mal armado desde la app no pueda guardar un subtotal que no cuadre con sus propios valores. Índice sobre `CompraDetalle.CompraId` (C-3).

**`sp_RegistrarCompra`** — lógica, con B-4 ya corregido:

1. Validar proveedor existente y activo. Validar TVP no vacío. Validar que **todos** los `ProductoId` del TVP existan (mensaje que nombre el código, no el Id).
2. Abrir transacción según C-5.
3. Insertar encabezado con `Total = SUM(Cantidad * CostoUnitario)` del TVP; capturar `SCOPE_IDENTITY()`.
4. Insertar el detalle tal cual viene, sin agrupar — cada línea del documento se conserva.
5. **Incrementar stock agrupando primero:**
   ```sql
   UPDATE p SET p.StockActual = p.StockActual + d.Cantidad
   FROM Inventario.Productos p
   INNER JOIN (SELECT ProductoId, SUM(Cantidad) AS Cantidad
               FROM @Detalle GROUP BY ProductoId) d ON d.ProductoId = p.Id;
   ```
6. Si `@EsCredito = 1`, crear la fila en `CuentasPorPagar` con vencimiento `DATEADD(DAY, ISNULL(@DiasCredito, 30), CAST(SYSDATETIME() AS DATE))`.
7. `COMMIT`, auditar **después** del commit (4.6), devolver `Exito`, `Mensaje`, `CompraId`.

`CuentasPorPagar` se define en la fase 6. En SSDT no importa el orden entre archivos: el modelo se resuelve completo al compilar.

### Fase 4 — Paquetes

**Archivos:** `Paquetes.sql`, `PaqueteDetalle.sql`, `Types/PaqueteDetalleTableType.sql`, `StoredProcedures/sp_ArmarPaquete.sql`.

Un paquete **es** un producto de `Inventario.Productos` (tiene código, precio e ISV propios) más una fila en `Repuestos.Paquetes` que lo marca como tal. No tiene stock propio: el stock que se mueve es el de sus componentes.

`PaqueteDetalle` con `CHECK (Cantidad > 0)`, `CHECK (ComponenteProductoId <> PaqueteId)` y `UNIQUE (PaqueteId, ComponenteProductoId)`. Índice sobre `PaqueteId`.

**La regla que un `CHECK` no puede expresar:** un componente no puede ser a su vez un paquete (nada de paquetes anidados), porque un `CHECK` no consulta otra tabla. Se valida en `sp_ArmarPaquete`.

**`sp_ArmarPaquete`** valida en orden: el producto del paquete existe; ningún componente es a su vez un paquete; el paquete no se contiene a sí mismo; todos los componentes existen y están activos. Luego, dentro de la transacción: inserta la fila en `Paquetes` si no existía, **borra el detalle previo** y reinserta desde el TVP — rearmado completo, no incremental.

> El borrado y reinserción es lo que hace posible el defecto B-7. Ver decisión D-3.

### Fase 5 — Ventas

**Archivos:** `Ventas.sql`, `VentaDetalle.sql`, `Types/VentaDetalleTableType.sql`, `sp_RegistrarVenta.sql`, `sp_AnularVenta.sql`, `sp_ObtenerProductoRepuesto.sql`.

`Ventas` con `NumeroFactura NVARCHAR(60) UNIQUE` (el correlativo completo entra: 40 + 1 + 16 = 57), `Subtotal`, `MontoISV`, `Total`, `UsuarioId`, `EsCredito`, `Anulada BIT DEFAULT 0`, `MotivoAnulacion`.

`VentaDetalle` guarda `PrecioUnitario` como **fotografía del precio al momento de vender**. Si el precio del producto cambia el mes que viene, las facturas ya emitidas no pueden cambiar de valor retroactivamente.

**`Anulada` en lugar de `DELETE`:** una factura con CAI emitido no se borra nunca. La fila se marca con su motivo.

Índices: `Ventas(Fecha)` filtrado por `Anulada = 0` (C-4) y `VentaDetalle(VentaId)` (C-3).

**`sp_RegistrarVenta`** — el SP más delicado del sistema. Lógica corregida con B-3, B-5 y B-6:

1. Validar TVP no vacío.
2. Validar que todos los `ProductoId` existan y estén **activos** (B-6), con mensaje que nombre el código.
3. **Expandir paquetes** a componentes reales en una tabla variable `@StockRequerido (ProductoId PK, CantidadRequerida)`: las líneas que no son paquete van tal cual; las que sí, se reemplazan por sus componentes multiplicados por la cantidad vendida. Todo agrupado con `SUM` — un mismo componente puede venir de dos paquetes distintos en la misma factura.
4. **Chequeo previo de stock, fuera de la transacción.** Filtro rápido para no quemar un correlativo en una venta condenada.
5. Abrir transacción (C-5).
6. **Re-validar stock dentro de la transacción con `WITH (UPDLOCK)`** sobre las filas de `@StockRequerido` (B-5). Si falla, `Exito = 0` con "Stock insuficiente" y salir limpio.
7. Obtener el correlativo llamando a `Facturacion.sp_ObtenerCorrelativoCAI` — ya corregido en 4.4 para no destruir esta transacción. Si `Exito = 0`, propagar el mensaje del CAI tal cual ("CAI vencido", "rango agotado") y salir.
8. Calcular montos sobre las **líneas comerciales**, no sobre los componentes expandidos: se factura el paquete a su precio, no la suma de sus partes.
9. Insertar encabezado, detalle, y si es crédito la fila de `CuentasPorCobrar` (vencimiento por defecto a 15 días).
10. Descontar stock con un solo `UPDATE ... FROM ... JOIN @StockRequerido`.
11. `COMMIT`; auditar después; devolver `Exito`, `Mensaje`, `NumeroFactura`, `Total`.

**Por qué el stock se valida antes de pedir el CAI:** pedir un correlativo consume un número del rango autorizado por el SAR. No se gasta un número en una venta que iba a fallar de todos modos.

**Sobre el correlativo y el rollback:** si la venta falla *después* del paso 7, el rollback revierte también el avance de `CorrelativoActual` y el número se reutiliza en la siguiente venta. Ese comportamiento es correcto —no quedan huecos en la numeración— pero es lo contrario de lo que afirmaba el plan anterior. Queda documentado como decidido: **el correlativo se consume solo si la venta se confirma.**

**`sp_AnularVenta`** — con B-8 pendiente de decisión (D-4). Valida que la venta exista y no esté ya anulada; restaura stock; marca `Anulada = 1` con motivo. La restauración debe usar la composición **guardada**, no la actual (B-7 / D-3).

**`sp_ObtenerProductoRepuesto`** devuelve tres result sets en una sola llamada —datos base con `LEFT JOIN DetalleProducto`, vehículos compatibles, números equivalentes—, que Dapper consume con `QueryMultipleAsync`. Un viaje a la base en vez de tres: en red local con una PC modesta, el costo dominante es la latencia por llamada, no el volumen.

### Fase 6 — Cuentas por cobrar y por pagar

**Archivos:** `CuentasPorCobrar.sql`, `PagoCuentaPorCobrar.sql`, `CuentasPorPagar.sql`, `PagoCuentaPorPagar.sql`, y los cuatro SPs de pago y listado.

**Alcance deliberadamente limitado:** control de crédito básico — saldo pendiente, pagos parciales, vencimiento. No es contabilidad: sin libro mayor ni partida doble. Eso excede el sistema simple que se está vendiendo.

Ambas tablas de cuentas llevan `MontoOriginal`, `SaldoPendiente`, `FechaVencimiento`, `Estado`, con `CHECK (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal)` y `CHECK (Estado IN ('Pendiente','PagadaParcial','Pagada'))`. `UNIQUE` sobre `VentaId` / `CompraId`: una cuenta por documento.

**`'Vencida'` no es un estado guardado.** Guardarlo obligaría a un proceso diario que actualice las cuentas vencidas —y Express no tiene SQL Server Agent—. En cambio se calcula al consultar: `SaldoPendiente > 0 AND FechaVencimiento < CAST(SYSDATETIME() AS DATE)`. Nunca queda un dato desactualizado esperando que alguien lo corrija.

Los SPs de pago validan que la cuenta exista y que el monto no exceda el saldo **antes** de aplicar nada, insertan el pago, y actualizan saldo y estado en la misma transacción. La lectura del saldo dentro de la transacción va con `WITH (UPDLOCK)`: dos pagos simultáneos sobre la misma cuenta son improbables pero el costo de protegerlo es cero.

Los SPs de listado reciben `@SoloConSaldo BIT = 1` y devuelven la columna calculada `EstaVencida`, paginados.

---

## 6. Rendimiento en PC de bajos recursos

Reglas que aplican a todo SP nuevo, derivadas de los límites reales de SQL Server Express: 1 GB de buffer pool, 4 cores de un socket, 10 GB por base.

**Paginación obligatoria en todo listado.** `OFFSET @Salto ROWS FETCH NEXT @TamanoPagina ROWS ONLY`, con el conteo total en un segundo result set. Ningún SP devuelve un conjunto de tamaño indeterminado.

**Nunca `SELECT *`.** Cada columna innecesaria es buffer pool gastado. Importa especialmente con `Configuracion.Logo`.

**Índices que cubren, no índices que existen.** Con 1 GB de caché, un índice que obliga a un *key lookup* por fila es peor que no tenerlo. El `INCLUDE` de C-2 es el patrón a seguir.

**`OPTION (RECOMPILE)` en las consultas con parámetros opcionales.** `sp_ListarProductos`, `sp_ListarProveedores`, los de cuentas. Recompilar cuesta milisegundos; ejecutar un plan cacheado para el parámetro equivocado cuesta segundos.

**Transacciones cortas.** Toda validación que no requiera bloqueo va antes del `BEGIN TRAN` (C-6). Una transacción larga en un sistema con dos cajas es la causa más común de "el sistema se trabó".

**`SET LOCK_TIMEOUT` en los puntos de contención.** Ya está en `sp_ObtenerCorrelativoCAI` (5 s) y es el patrón correcto: fallar con un mensaje claro es mejor que dejar la caja esperando sin explicación. Aplicarlo también en los SPs de pago.

**Sin `NOLOCK`.** Tentador para reportes, pero produce lecturas sucias y filas duplicadas o ausentes. En un sistema donde el número que se lee es dinero, no.

**Mantenimiento sin Agent.** Express no trae SQL Server Agent, así que `Sistemas.Mantenimiento` es quien dispara: reconstrucción de índices y `UPDATE STATISTICS` semanal, purga de auditoría mensual, `DBCC CHECKDB` semanal.

---

## 7. Fiabilidad ante cortes de energía

El escenario a resistir: se va la luz en medio de una venta, con la factura ya impresa.

**Modelo de recuperación `SIMPLE`.** Sin personal técnico en sitio, nadie va a administrar el log de transacciones ni a hacer respaldos de log. `SIMPLE` trunca el log en cada checkpoint y evita que crezca hasta llenar el disco — la falla más común en instalaciones desatendidas. El costo es no poder recuperar a un punto en el tiempo, lo que se compensa con respaldos frecuentes. `FULL` sin mantenimiento de log es peor que `SIMPLE`.

**Durabilidad completa, sin excepción.** `DELAYED_DURABILITY` debe quedar en `DISABLED` explícitamente. Acelera confirmando antes de escribir el log a disco, y eso significa perder transacciones ya confirmadas ante un corte. Es exactamente el intercambio que este producto no puede aceptar.

**Atomicidad como garantía de recuperación.** La razón de fondo por la que toda venta va en una sola transacción no es elegancia: si la luz se va a la mitad, SQL Server al reiniciar deshace la transacción incompleta y la base queda consistente. Una venta a medias —encabezado sin detalle, o stock descontado sin factura— es lo que produce inventarios que no cuadran y nadie sabe por qué.

**`AUTO_CLOSE` en `OFF`.** Está en `ON` por defecto en algunas ediciones Express: cierra la base cuando no hay conexiones y la reabre en la siguiente, con un retraso visible en la primera operación del día y riesgo adicional si el cierre coincide con un corte.

**Respaldo automático — es producto, no infraestructura.** `Sistemas.Mantenimiento.BackupService` debe existir antes de la primera instalación real:
- `BACKUP DATABASE ... WITH COMPRESSION, CHECKSUM` diario. **`CHECKSUM` no es opcional**: valida las páginas al respaldar, de modo que un respaldo corrupto se detecta al hacerlo y no seis meses después cuando se necesita.
- Retención por N copias, con borrado de las viejas — el disco de estas máquinas es chico.
- Destino en una unidad distinta a la de la base, idealmente una USB. Un respaldo en el mismo disco no protege del fallo de disco.
- `RESTORE VERIFYONLY` después de cada respaldo. Un respaldo que nunca se verificó no es un respaldo.

**`DBCC CHECKDB` semanal.** Los cortes de energía repetidos corrompen páginas. Detectarlo temprano, cuando todavía hay respaldos sanos, es la diferencia entre restaurar un día de trabajo y perder el historial completo.

**`PAGE_VERIFY CHECKSUM`** activo en la base. Detecta corrupción al leer, no al fallar.

**Verificación al arrancar la aplicación.** Antes de abrir la caja, la app consulta un `Configuracion.sp_VerificarEstadoSistema` que devuelve: versión de esquema, fecha del último respaldo exitoso, y si el CAI activo está por vencerse o por agotarse. Que el dueño se entere de que hace 40 días no hay respaldo *antes* de necesitarlo.

---

## 8. Versionado y despliegue

**Un DACPAC por vertical.** El `.sqlproj` compila a `.dacpac`; la publicación compara el modelo contra la base instalada y genera el script de diferencias. Es lo que hace viable actualizar 30 instalaciones offline sin escribir migraciones a mano.

**Reglas de publicación para producción:**
- `BlockOnPossibleDataLoss = True`. Si una actualización va a perder datos, debe fallar y avisar, no proceder.
- `DropObjectsNotInSource = False`. Nunca borrar lo que el modelo no conoce.
- Respaldo obligatorio **antes** de publicar, verificado con `RESTORE VERIFYONLY`.

**`Configuracion.VersionEsquema` se actualiza en el script post-despliegue** de cada publicación. Es la única forma de responder por teléfono "¿en qué versión está este cliente?".

**Datos semilla en script post-despliegue idempotente.** Los roles `Administrador` y `Operador` se insertan con `IF NOT EXISTS`, de modo que reejecutar la publicación no duplique nada.

---

## 9. Pruebas mínimas antes de entregar

No hace falta un framework. Un script `.sql` por escenario, ejecutable contra una base limpia, que verifique el resultado esperado. Estos son los que no pueden faltar, y cada uno cubre un defecto real encontrado en la revisión:

1. **Venta con paquete** — verificar que el stock descontado sea el de los componentes, no el del paquete.
2. **Venta con stock insuficiente** — devuelve `Exito = 0` con mensaje claro, **y el correlativo CAI no avanzó**.
3. **Venta con CAI vencido** — mensaje "CAI vencido", sin error 3903, sin transacción huérfana. *(Cubre B-3.)*
4. **Compra con el mismo producto en dos líneas** — el stock sube por la **suma** de ambas. *(Cubre B-4.)*
5. **Dos ventas simultáneas** — dos sesiones pidiendo correlativo a la vez reciben números distintos.
6. **Anulación de venta con paquete** — el stock devuelto es idéntico al descontado. *(Cubre B-7.)*
7. **Pago mayor al saldo** — rechazado antes de tocar nada.
8. **Primer guardado de configuración con un usuario que solo tiene `EXECUTE`** — debe funcionar. *(Cubre B-2.)*
9. **Importación masiva con una fila inválida** — las válidas entran, la mala se reporta con su código.
10. **Corte simulado** — matar el proceso de SQL Server a mitad de una venta; al reiniciar, ni la venta ni el descuento de stock deben existir.

La prueba 10 es la que valida la promesa central del producto en este mercado. Vale la pena hacerla una vez, a mano, y documentar el resultado.

---

## 10. Decisiones pendientes

Estas requieren definición del negocio, no del desarrollador. Ninguna se asume por cuenta propia.

**D-1 — Collation de la base.** La actual (`1033, CI`) es acento-sensitiva: `bujia` no encuentra `bujía`, `cigueñal` no encuentra `cigüeñal`. En una tienda donde el vendedor teclea rápido y sin tildes, esto se traduce en "el sistema dice que no hay" sobre producto que sí está en bodega. Cambiar a una collation **acento-insensitiva** (`Modern_Spanish_CI_AI` o `Latin1_General_CI_AI`) lo resuelve. **Debe decidirse antes de la primera instalación**: cambiar la collation con datos ya cargados es una migración completa, no un `ALTER`.

**D-2 — Estrategia de búsqueda de productos.** El `LIKE '%texto%'` actual no usa índice (C-1). Opciones: (a) aceptarlo, viable hasta unos 5 000 productos; (b) buscar por prefijo `LIKE 'texto%'`, que sí usa índice pero cambia el comportamiento esperado; (c) Full-Text Search, que Express soporta pero agrega complejidad de instalación. Recomendación: (a) ahora, medir con el catálogo real del primer cliente, y decidir con datos.

**D-3 — Composición histórica de los paquetes (B-7).** Si un paquete se rearma después de vendido, la anulación devuelve componentes equivocados. Opciones: (a) guardar en `VentaDetalle` las líneas expandidas además de la línea comercial —más filas, corrección total—; (b) versionar `PaqueteDetalle` con vigencia; (c) prohibir rearmar un paquete que ya tiene ventas, y obligar a crear uno nuevo. Recomendación: **(c)**, que es la más simple, la más barata de implementar y la más fácil de explicar al usuario.

**D-4 — Anulación de venta a crédito con pagos ya recibidos (B-8).** ¿Se cancela la cuenta por cobrar completa? ¿Qué pasa con el dinero ya cobrado — se genera una nota de crédito, se devuelve, queda a favor del cliente? Es una regla de negocio, y hasta que exista, `sp_AnularVenta` debe **rechazar** anular una venta a crédito con pagos registrados, en vez de dejar el estado inconsistente que produce hoy.

**D-5 — Procedimiento formal de anulación ante el SAR.** El principio de no reutilizar un correlativo emitido es general, pero cómo debe quedar registrada formalmente una anulación conviene confirmarlo con un contador o asesor fiscal actualizado, no asumirlo desde el diseño.

**D-6 — Versión mínima de SQL Server a soportar.** El `.sqlproj` apunta hoy a SQL Server 2022 (`Sql170`). Debe fijarse a la versión más baja que se vaya a instalar en un cliente real, no a la más nueva disponible en la máquina de desarrollo.

---

## 11. Orden de trabajo sugerido

1. **Fase 0 completa** (sección 4). Sin esto no se puede probar nada, y arrastrar B-3 a la vertical significa depurarlo dentro del SP más complejo del sistema en lugar de aislado.
2. **Decidir D-1** antes de crear cualquier base con datos reales.
3. **Fases 1 a 6** en orden.
4. **Pruebas de la sección 9** conforme cada fase cierra, no todas al final.
5. **`Sistemas.Mantenimiento`** (respaldo, purga, `CHECKDB`) antes de la primera instalación en un cliente real. Es lo único de esta lista cuya ausencia puede costar el negocio entero de un cliente.

---

## Anexo A — DDL exacto

Todo lo que sigue es literal: tipos, nombres de constraint e índices tal cual deben quedar. **Los `DEFAULT` van siempre con nombre explícito** (`CONSTRAINT DF_...`) — si no se nombran, SQL Server genera un nombre aleatorio distinto en cada instalación y SSDT lo detecta como diferencia en cada publicación, produciendo scripts de actualización ruidosos en los clientes.

### A.1 Correcciones al DDL de Core

**`Configuracion/Tables/Configuracion.sql` — reemplazo completo (defecto B-2).**

```sql
CREATE TABLE Configuracion.Configuracion (
    Id                  INT             NOT NULL,
    NombreComercial     NVARCHAR(150)   NOT NULL,
    RTN                 CHAR(14)        NOT NULL,
    Direccion           NVARCHAR(300)   NULL,
    Telefono            NVARCHAR(20)    NULL,
    CorreoContacto      NVARCHAR(100)   NULL,
    Logo                VARBINARY(MAX)  NULL,
    FechaActualizacion  DATETIME2(0)    NOT NULL CONSTRAINT DF_Configuracion_FechaActualizacion DEFAULT SYSDATETIME(),
    CONSTRAINT PK_Configuracion PRIMARY KEY (Id),
    CONSTRAINT CK_Configuracion_RTN_Formato CHECK (RTN NOT LIKE '%[^0-9]%' AND LEN(RTN) = 14),
    CONSTRAINT CK_Configuracion_Singleton CHECK (Id = 1)
);
GO
```

Sin `IDENTITY`. `sp_GuardarConfiguracion` inserta el literal `1` y se elimina todo `SET IDENTITY_INSERT`.

**`Configuracion/Tables/VersionEsquema.sql` — nueva (tarea 4.11).**

```sql
CREATE TABLE Configuracion.VersionEsquema (
    Id              INT             IDENTITY(1,1) NOT NULL,
    Version         NVARCHAR(20)    NOT NULL,
    Vertical        NVARCHAR(50)    NOT NULL,
    FechaAplicacion DATETIME2(0)    NOT NULL CONSTRAINT DF_VersionEsquema_Fecha DEFAULT SYSDATETIME(),
    CONSTRAINT PK_VersionEsquema PRIMARY KEY (Id),
    CONSTRAINT UQ_VersionEsquema UNIQUE (Vertical, Version)
);
GO
```

**Índices de `Inventario.Productos` (tarea 4.8).** Eliminar `IX_Productos_Activo` y crear:

```sql
CREATE INDEX IX_Productos_Activo_Nombre
    ON Inventario.Productos(Nombre)
    INCLUDE (Codigo, PrecioUnitario, StockActual, StockMinimo, CategoriaId, TasaISV)
    WHERE Activo = 1;
GO
```

`IX_Productos_CategoriaId` se conserva sin cambios.

**`Facturacion/Functions/fn_CalcularISV.sql` (tarea 4.5).** Idéntica, más `WITH SCHEMABINDING`:

```sql
CREATE FUNCTION Facturacion.fn_CalcularISV
(
    @Monto      DECIMAL(12,2),
    @TasaISV    DECIMAL(5,2)
)
RETURNS DECIMAL(12,2)
WITH SCHEMABINDING
AS
BEGIN
    RETURN ROUND(@Monto * @TasaISV / 100.0, 2);
END
GO
```

### A.2 Fase 1 — Extensión de catálogo

```sql
CREATE TABLE Repuestos.DetalleProducto (
    ProductoId      INT             NOT NULL,
    NumeroParte     NVARCHAR(50)    NULL,
    MarcaFabricante NVARCHAR(50)    NULL,
    EsOriginal      BIT             NOT NULL CONSTRAINT DF_DetalleProducto_EsOriginal DEFAULT 1,
    CONSTRAINT PK_DetalleProducto PRIMARY KEY (ProductoId),
    CONSTRAINT FK_DetalleProducto_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id)
);
GO

CREATE INDEX IX_DetalleProducto_NumeroParte
    ON Repuestos.DetalleProducto(NumeroParte)
    WHERE NumeroParte IS NOT NULL;
GO
```

`ProductoId` es PK y FK a la vez: eso es lo que hace la relación 1:1. Es **opcional** — un insumo genérico (grasa, trapos) no tiene fila acá, por eso toda consulta usa `LEFT JOIN`.

```sql
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

CREATE INDEX IX_VehiculoCompatible_MarcaModelo ON Repuestos.VehiculoCompatible(Marca, Modelo) INCLUDE (ProductoId, AnioDesde, AnioHasta);
CREATE INDEX IX_VehiculoCompatible_ProductoId ON Repuestos.VehiculoCompatible(ProductoId);
GO
```

**Atención:** el plan anterior tenía `CHECK (AnioDesde BETWEEN 1950 AND YEAR(GETDATE()) + 1)`. **`GETDATE()` no es determinística y SQL Server no la admite en un `CHECK`** — no compila. El tope superior (año actual + 1) se valida en `sp_AgregarVehiculoCompatible`, no en la tabla.

```sql
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

CREATE INDEX IX_NumeroEquivalente_NumeroOEM ON Repuestos.NumeroEquivalente(NumeroOEM) INCLUDE (ProductoId, Fabricante);
GO
```

### A.3 Fase 2 — Proveedores

```sql
CREATE TABLE Repuestos.Proveedores (
    Id          INT             IDENTITY(1,1) NOT NULL,
    Nombre      NVARCHAR(150)   NOT NULL,
    RTN         CHAR(14)        NULL,
    Telefono    NVARCHAR(20)    NULL,
    Contacto    NVARCHAR(100)   NULL,
    Activo      BIT             NOT NULL CONSTRAINT DF_Proveedores_Activo DEFAULT 1,
    CONSTRAINT PK_Proveedores PRIMARY KEY (Id),
    CONSTRAINT UQ_Proveedores_Nombre UNIQUE (Nombre),
    CONSTRAINT CK_Proveedores_RTN CHECK (RTN IS NULL OR (LEN(RTN) = 14 AND RTN NOT LIKE '%[^0-9]%'))
);
GO

CREATE TABLE Repuestos.ProductoProveedor (
    ProductoId      INT             NOT NULL,
    ProveedorId     INT             NOT NULL,
    PrecioCompra    DECIMAL(12,2)   NOT NULL,
    CONSTRAINT PK_ProductoProveedor PRIMARY KEY (ProductoId, ProveedorId),
    CONSTRAINT FK_ProductoProveedor_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT FK_ProductoProveedor_Proveedores FOREIGN KEY (ProveedorId) REFERENCES Repuestos.Proveedores(Id),
    CONSTRAINT CK_ProductoProveedor_Precio CHECK (PrecioCompra >= 0)
);
GO

CREATE INDEX IX_ProductoProveedor_ProveedorId ON Repuestos.ProductoProveedor(ProveedorId);
GO
```

La PK compuesta cubre las búsquedas por `ProductoId`; el índice extra cubre la dirección contraria ("qué me vende este proveedor").

### A.4 Fase 3 — Compras

```sql
CREATE TABLE Repuestos.Compras (
    Id                      INT             IDENTITY(1,1) NOT NULL,
    ProveedorId             INT             NOT NULL,
    NumeroFacturaProveedor  NVARCHAR(30)    NULL,
    Fecha                   DATETIME2(0)    NOT NULL CONSTRAINT DF_Compras_Fecha DEFAULT SYSDATETIME(),
    Total                   DECIMAL(12,2)   NOT NULL CONSTRAINT DF_Compras_Total DEFAULT 0,
    UsuarioId               INT             NOT NULL,
    EsCredito               BIT             NOT NULL CONSTRAINT DF_Compras_EsCredito DEFAULT 0,
    CONSTRAINT PK_Compras PRIMARY KEY (Id),
    CONSTRAINT FK_Compras_Proveedores FOREIGN KEY (ProveedorId) REFERENCES Repuestos.Proveedores(Id),
    CONSTRAINT FK_Compras_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_Compras_Total CHECK (Total >= 0)
);
GO

CREATE INDEX IX_Compras_ProveedorId ON Repuestos.Compras(ProveedorId);
CREATE INDEX IX_Compras_Fecha ON Repuestos.Compras(Fecha DESC);
GO

CREATE TABLE Repuestos.CompraDetalle (
    Id              INT             IDENTITY(1,1) NOT NULL,
    CompraId        INT             NOT NULL,
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL,
    Subtotal        AS (Cantidad * CostoUnitario) PERSISTED,
    CONSTRAINT PK_CompraDetalle PRIMARY KEY (Id),
    CONSTRAINT FK_CompraDetalle_Compras FOREIGN KEY (CompraId) REFERENCES Repuestos.Compras(Id),
    CONSTRAINT FK_CompraDetalle_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_CompraDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_CompraDetalle_Costo CHECK (CostoUnitario >= 0)
);
GO

CREATE INDEX IX_CompraDetalle_CompraId ON Repuestos.CompraDetalle(CompraId) INCLUDE (ProductoId, Cantidad, CostoUnitario);
CREATE INDEX IX_CompraDetalle_ProductoId ON Repuestos.CompraDetalle(ProductoId);
GO

CREATE TYPE Repuestos.CompraDetalleTableType AS TABLE (
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    CostoUnitario   DECIMAL(12,2)   NOT NULL
);
GO
```

### A.5 Fase 4 — Paquetes

```sql
CREATE TABLE Repuestos.Paquetes (
    ProductoId  INT NOT NULL,
    CONSTRAINT PK_Paquetes PRIMARY KEY (ProductoId),
    CONSTRAINT FK_Paquetes_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id)
);
GO

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

CREATE INDEX IX_PaqueteDetalle_ComponenteProductoId ON Repuestos.PaqueteDetalle(ComponenteProductoId);
GO

CREATE TYPE Repuestos.PaqueteDetalleTableType AS TABLE (
    ComponenteProductoId    INT NOT NULL,
    Cantidad                INT NOT NULL
);
GO
```

El `UNIQUE (PaqueteId, ComponenteProductoId)` ya sirve como índice para la expansión de paquetes en la venta; no hace falta uno adicional sobre `PaqueteId`.

### A.6 Fase 5 — Ventas

```sql
CREATE TABLE Repuestos.Ventas (
    Id              INT             IDENTITY(1,1) NOT NULL,
    NumeroFactura   NVARCHAR(60)    NOT NULL,
    Fecha           DATETIME2(0)    NOT NULL CONSTRAINT DF_Ventas_Fecha DEFAULT SYSDATETIME(),
    Subtotal        DECIMAL(12,2)   NOT NULL,
    MontoISV        DECIMAL(12,2)   NOT NULL,
    Total           DECIMAL(12,2)   NOT NULL,
    UsuarioId       INT             NOT NULL,
    EsCredito       BIT             NOT NULL CONSTRAINT DF_Ventas_EsCredito DEFAULT 0,
    Anulada         BIT             NOT NULL CONSTRAINT DF_Ventas_Anulada DEFAULT 0,
    MotivoAnulacion NVARCHAR(200)   NULL,
    FechaAnulacion  DATETIME2(0)    NULL,
    CONSTRAINT PK_Ventas PRIMARY KEY (Id),
    CONSTRAINT UQ_Ventas_NumeroFactura UNIQUE (NumeroFactura),
    CONSTRAINT FK_Ventas_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_Ventas_Subtotal CHECK (Subtotal >= 0),
    CONSTRAINT CK_Ventas_MontoISV CHECK (MontoISV >= 0),
    CONSTRAINT CK_Ventas_Total CHECK (Total >= 0),
    CONSTRAINT CK_Ventas_Anulacion CHECK (
        (Anulada = 0 AND MotivoAnulacion IS NULL AND FechaAnulacion IS NULL)
     OR (Anulada = 1 AND MotivoAnulacion IS NOT NULL AND FechaAnulacion IS NOT NULL))
);
GO

CREATE INDEX IX_Ventas_Fecha ON Repuestos.Ventas(Fecha DESC) INCLUDE (NumeroFactura, Total, UsuarioId) WHERE Anulada = 0;
CREATE INDEX IX_Ventas_UsuarioId ON Repuestos.Ventas(UsuarioId);
GO
```

`FechaAnulacion` no estaba en el plan anterior. Se agrega porque sin ella no se puede responder "¿qué se anuló ayer?", que es justo lo que pregunta el dueño cuando la caja no cuadra. El `CK_Ventas_Anulacion` garantiza que los tres campos de anulación se muevan juntos: no puede existir una venta anulada sin motivo ni fecha, ni un motivo en una venta viva.

```sql
CREATE TABLE Repuestos.VentaDetalle (
    Id              INT             IDENTITY(1,1) NOT NULL,
    VentaId         INT             NOT NULL,
    ProductoId      INT             NOT NULL,
    Cantidad        INT             NOT NULL,
    PrecioUnitario  DECIMAL(12,2)   NOT NULL,
    TasaISV         DECIMAL(5,2)    NOT NULL,
    Subtotal        AS (Cantidad * PrecioUnitario) PERSISTED,
    CONSTRAINT PK_VentaDetalle PRIMARY KEY (Id),
    CONSTRAINT FK_VentaDetalle_Ventas FOREIGN KEY (VentaId) REFERENCES Repuestos.Ventas(Id),
    CONSTRAINT FK_VentaDetalle_Productos FOREIGN KEY (ProductoId) REFERENCES Inventario.Productos(Id),
    CONSTRAINT CK_VentaDetalle_Cantidad CHECK (Cantidad > 0),
    CONSTRAINT CK_VentaDetalle_Precio CHECK (PrecioUnitario >= 0),
    CONSTRAINT CK_VentaDetalle_TasaISV CHECK (TasaISV IN (0.00, 15.00, 18.00))
);
GO

CREATE INDEX IX_VentaDetalle_VentaId ON Repuestos.VentaDetalle(VentaId) INCLUDE (ProductoId, Cantidad, PrecioUnitario, TasaISV);
CREATE INDEX IX_VentaDetalle_ProductoId ON Repuestos.VentaDetalle(ProductoId);
GO

CREATE TYPE Repuestos.VentaDetalleTableType AS TABLE (
    ProductoId  INT NOT NULL,
    Cantidad    INT NOT NULL
);
GO
```

`TasaISV` tampoco estaba en el plan anterior, y es un error del mismo tipo que faltaba corregir junto con `PrecioUnitario`: si la tasa de un producto cambia (una reforma fiscal, o simplemente una corrección de captura), reimprimir una factura vieja daría un ISV distinto al que se le cobró al cliente y al que se declaró. La tasa se congela junto con el precio.

### A.7 Fase 6 — Cuentas por cobrar y por pagar

```sql
CREATE TABLE Repuestos.CuentasPorCobrar (
    Id                  INT             IDENTITY(1,1) NOT NULL,
    VentaId             INT             NOT NULL,
    MontoOriginal       DECIMAL(12,2)   NOT NULL,
    SaldoPendiente      DECIMAL(12,2)   NOT NULL,
    FechaVencimiento    DATE            NOT NULL,
    Estado              NVARCHAR(20)    NOT NULL CONSTRAINT DF_CuentasPorCobrar_Estado DEFAULT 'Pendiente',
    CONSTRAINT PK_CuentasPorCobrar PRIMARY KEY (Id),
    CONSTRAINT UQ_CuentasPorCobrar_VentaId UNIQUE (VentaId),
    CONSTRAINT FK_CuentasPorCobrar_Ventas FOREIGN KEY (VentaId) REFERENCES Repuestos.Ventas(Id),
    CONSTRAINT CK_CuentasPorCobrar_Montos CHECK (SaldoPendiente >= 0 AND SaldoPendiente <= MontoOriginal),
    CONSTRAINT CK_CuentasPorCobrar_MontoOriginal CHECK (MontoOriginal > 0),
    CONSTRAINT CK_CuentasPorCobrar_Estado CHECK (Estado IN ('Pendiente', 'PagadaParcial', 'Pagada', 'Anulada'))
);
GO

CREATE INDEX IX_CuentasPorCobrar_Vencimiento ON Repuestos.CuentasPorCobrar(FechaVencimiento) WHERE SaldoPendiente > 0;
GO

CREATE TABLE Repuestos.PagoCuentaPorCobrar (
    Id                  INT             IDENTITY(1,1) NOT NULL,
    CuentaPorCobrarId   INT             NOT NULL,
    Monto               DECIMAL(12,2)   NOT NULL,
    Fecha               DATETIME2(0)    NOT NULL CONSTRAINT DF_PagoCPC_Fecha DEFAULT SYSDATETIME(),
    MetodoPago          NVARCHAR(30)    NULL,
    UsuarioId           INT             NOT NULL,
    CONSTRAINT PK_PagoCuentaPorCobrar PRIMARY KEY (Id),
    CONSTRAINT FK_PagoCPC_CuentaPorCobrar FOREIGN KEY (CuentaPorCobrarId) REFERENCES Repuestos.CuentasPorCobrar(Id),
    CONSTRAINT FK_PagoCPC_Usuarios FOREIGN KEY (UsuarioId) REFERENCES Security.Usuarios(Id),
    CONSTRAINT CK_PagoCPC_Monto CHECK (Monto > 0)
);
GO

CREATE INDEX IX_PagoCPC_CuentaPorCobrarId ON Repuestos.PagoCuentaPorCobrar(CuentaPorCobrarId);
GO
```

`CuentasPorPagar` y `PagoCuentaPorPagar` son **estructuralmente idénticas**, cambiando `VentaId → CompraId`, la FK a `Repuestos.Compras(Id)`, y los prefijos `CPC → CPP`. El estado `'Anulada'` se agrega a ambas para poder cerrar la cuenta cuando se anula el documento origen (decisión D-4).

El índice filtrado por `SaldoPendiente > 0` es el que sostiene la pantalla de cobros: solo indexa las cuentas vivas, que son una fracción del histórico.

---

## Anexo B — Cuerpos de los SP no triviales

Los SP que aquí no aparecen (`sp_GuardarProveedor`, `sp_ListarProveedores`, `sp_AgregarVehiculoCompatible`, `sp_GuardarDetalleProducto`, etc.) son mecánicos: aplicar la plantilla C-5 y el contrato C-4 alcanza. Los que siguen son los que tienen lógica que se puede equivocar.

### B.1 `Facturacion.sp_ObtenerCorrelativoCAI` — corregido (defecto B-3)

Reemplaza al archivo actual por completo. El cambio esencial: **nunca hace `ROLLBACK` de una transacción que no abrió.**

```sql
CREATE PROCEDURE Facturacion.sp_ObtenerCorrelativoCAI
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000;   -- la caja nunca espera indefinidamente

    DECLARE @TranPropia BIT = 0;
    DECLARE @Id INT, @RangoAutorizado NVARCHAR(40), @CorrelativoActual CHAR(16),
            @RangoFinal CHAR(16), @FechaVencimiento DATE, @Siguiente CHAR(16);

    BEGIN TRY
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCAI;

        -- UPDLOCK + HOLDLOCK: dos cajas simultáneas nunca leen el mismo correlativo.
        -- La segunda espera a que la primera confirme y lee el valor ya avanzado.
        SELECT
            @Id                = Id,
            @RangoAutorizado   = RangoAutorizado,
            @CorrelativoActual = CorrelativoActual,
            @RangoFinal        = RangoFinal,
            @FechaVencimiento  = FechaVencimiento
        FROM Facturacion.ConfiguracionCAI WITH (UPDLOCK, HOLDLOCK)
        WHERE Activo = 1;

        IF @Id IS NULL
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
            SELECT CAST(0 AS BIT) AS Exito,
                   'No hay un CAI activo configurado' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
            RETURN;
        END

        IF @FechaVencimiento < CAST(SYSDATETIME() AS DATE)
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
            SELECT CAST(0 AS BIT) AS Exito,
                   'El CAI configurado está vencido' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
            RETURN;
        END

        IF @CorrelativoActual >= @RangoFinal
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCAI;
            SELECT CAST(0 AS BIT) AS Exito,
                   'El rango de CAI se agotó, contactar al administrador' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
            RETURN;
        END

        SET @Siguiente = RIGHT('0000000000000000'
                             + CAST(CAST(@CorrelativoActual AS BIGINT) + 1 AS NVARCHAR(16)), 16);

        UPDATE Facturacion.ConfiguracionCAI
        SET CorrelativoActual = @Siguiente
        WHERE Id = @Id;

        IF @TranPropia = 1 COMMIT;

        SELECT CAST(1 AS BIT) AS Exito,
               'OK' AS Mensaje,
               @RangoAutorizado + '-' + @Siguiente AS Correlativo;
    END TRY
    BEGIN CATCH
        DECLARE @ErrorNumero     INT            = ERROR_NUMBER();
        DECLARE @ErrorMsgTecnico NVARCHAR(2000) = ERROR_MESSAGE();
        DECLARE @RefError        NVARCHAR(50)   = 'CAI-' + CONVERT(NVARCHAR(30), SYSDATETIME(), 120);

        IF XACT_STATE() = -1
            ROLLBACK;                                   -- condenada: no queda otra
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK;
            ELSE ROLLBACK TRANSACTION PuntoCAI;
        END

        -- Se audita DESPUÉS de deshacer, nunca dentro de la transacción (defecto B-9)
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId     = NULL,
            @Accion        = 'ERROR_SP',
            @TablaAfectada = 'Facturacion.ConfiguracionCAI',
            @RegistroId    = @RefError,
            @Detalle       = @ErrorMsgTecnico;

        IF @ErrorNumero = 1222   -- lock timeout
            SELECT CAST(0 AS BIT) AS Exito,
                   'Sistema ocupado procesando otra venta, intente nuevamente' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
        ELSE
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('Error interno al generar el correlativo. Referencia: ', @RefError) AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS Correlativo;
    END CATCH
END
GO
```

**Por qué `ROLLBACK TRANSACTION PuntoCAI` y no `ROLLBACK` a secas cuando está anidado:** deshacer hasta el savepoint revierte solo lo que hizo este SP y **deja viva la transacción del llamador**, que así puede devolver su propio mensaje ordenado. Un `ROLLBACK` completo la destruiría y `sp_RegistrarVenta` reventaría después con el error 3903. Deshacer a un savepoint no libera los bloqueos tomados —se sueltan al terminar la transacción externa—, lo cual acá es lo correcto: el `UPDLOCK` sobre el CAI debe sostenerse mientras la venta siga viva.

### B.2 `Repuestos.sp_RegistrarCompra`

```sql
CREATE PROCEDURE Repuestos.sp_RegistrarCompra
    @ProveedorId            INT,
    @NumeroFacturaProveedor NVARCHAR(30) = NULL,
    @UsuarioId              INT,
    @EsCredito              BIT = 0,
    @DiasCredito            INT = NULL,
    @Detalle                Repuestos.CompraDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;
    DECLARE @CompraId INT, @Total DECIMAL(12,2), @ProductoInvalido INT;

    BEGIN TRY
        ---------- Validaciones previas (fuera de transacción, regla C-6) ----------
        IF NOT EXISTS (SELECT 1 FROM Repuestos.Proveedores WHERE Id = @ProveedorId AND Activo = 1)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Proveedor no válido o inactivo' AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM @Detalle)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La compra debe tener al menos un producto' AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Detalle WHERE Cantidad <= 0 OR CostoUnitario < 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'Hay líneas con cantidad menor o igual a cero, o costo negativo' AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        SELECT TOP (1) @ProductoInvalido = d.ProductoId
        FROM @Detalle d
        WHERE NOT EXISTS (SELECT 1 FROM Inventario.Productos p WHERE p.Id = d.ProductoId);

        IF @ProductoInvalido IS NOT NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('El producto con Id ', @ProductoInvalido, ' no existe') AS Mensaje,
                   CAST(NULL AS INT) AS CompraId;
            RETURN;
        END

        SET @Total = (SELECT SUM(Cantidad * CostoUnitario) FROM @Detalle);

        ---------- Transacción ----------
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoCompra;

        INSERT INTO Repuestos.Compras (ProveedorId, NumeroFacturaProveedor, Total, UsuarioId, EsCredito)
        VALUES (@ProveedorId, @NumeroFacturaProveedor, @Total, @UsuarioId, @EsCredito);

        SET @CompraId = SCOPE_IDENTITY();

        -- El detalle se guarda tal cual viene: cada línea del documento se conserva.
        INSERT INTO Repuestos.CompraDetalle (CompraId, ProductoId, Cantidad, CostoUnitario)
        SELECT @CompraId, ProductoId, Cantidad, CostoUnitario FROM @Detalle;

        -- DEFECTO B-4: el stock SÍ se agrupa. Sin el GROUP BY, un producto que
        -- aparece en dos líneas incrementa una sola vez y el resto se pierde en silencio.
        UPDATE p
        SET p.StockActual = p.StockActual + d.Cantidad
        FROM Inventario.Productos p
        INNER JOIN (SELECT ProductoId, SUM(Cantidad) AS Cantidad
                    FROM @Detalle
                    GROUP BY ProductoId) d ON d.ProductoId = p.Id;

        IF @EsCredito = 1
        BEGIN
            INSERT INTO Repuestos.CuentasPorPagar (CompraId, MontoOriginal, SaldoPendiente, FechaVencimiento)
            VALUES (@CompraId, @Total, @Total,
                    DATEADD(DAY, ISNULL(@DiasCredito, 30), CAST(SYSDATETIME() AS DATE)));
        END

        IF @TranPropia = 1 COMMIT;

        -- Auditoría DESPUÉS del commit (defecto B-9): si falla, la compra ya está guardada.
        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'COMPRA_REGISTRADA',
            @TablaAfectada = 'Repuestos.Compras',
            @RegistroId = @CompraId, @Detalle = @NumeroFacturaProveedor;

        SELECT CAST(1 AS BIT) AS Exito, 'Compra registrada' AS Mensaje, @CompraId AS CompraId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoCompra;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje, CAST(NULL AS INT) AS CompraId;
    END CATCH
END
GO
```

### B.3 `Repuestos.sp_ArmarPaquete`

**Asume la decisión D-3 resuelta como opción (c):** no se permite rearmar un paquete que ya tiene ventas. Si el negocio elige otra opción, este SP cambia.

```sql
CREATE PROCEDURE Repuestos.sp_ArmarPaquete
    @ProductoIdPaquete  INT,
    @UsuarioId          INT,
    @Componentes        Repuestos.PaqueteDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM Inventario.Productos WHERE Id = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'El producto del paquete no existe: creelo primero como producto' AS Mensaje;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM @Componentes)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El paquete debe tener al menos un componente' AS Mensaje;
            RETURN;
        END

        -- Regla que un CHECK no puede expresar: no se permiten paquetes anidados,
        -- porque un CHECK no puede consultar otra tabla.
        IF EXISTS (SELECT 1 FROM @Componentes c
                   INNER JOIN Repuestos.Paquetes p ON p.ProductoId = c.ComponenteProductoId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'No se permiten paquetes anidados: un componente no puede ser otro paquete' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes WHERE ComponenteProductoId = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El paquete no puede contenerse a sí mismo' AS Mensaje;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Componentes c
                   INNER JOIN Inventario.Productos p ON p.Id = c.ComponenteProductoId
                   WHERE p.Activo = 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay componentes inactivos en la lista' AS Mensaje;
            RETURN;
        END

        -- DECISIÓN D-3 (c): rearmar un paquete ya vendido rompería la anulación,
        -- porque se devolverían al inventario componentes distintos a los que salieron.
        IF EXISTS (SELECT 1 FROM Repuestos.Paquetes pq
                   WHERE pq.ProductoId = @ProductoIdPaquete)
           AND EXISTS (SELECT 1 FROM Repuestos.VentaDetalle vd
                       WHERE vd.ProductoId = @ProductoIdPaquete)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'Este paquete ya tiene ventas registradas y no puede modificarse. Cree un paquete nuevo.' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoPaquete;

        IF NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes WHERE ProductoId = @ProductoIdPaquete)
            INSERT INTO Repuestos.Paquetes (ProductoId) VALUES (@ProductoIdPaquete);
        ELSE
            DELETE FROM Repuestos.PaqueteDetalle WHERE PaqueteId = @ProductoIdPaquete;

        INSERT INTO Repuestos.PaqueteDetalle (PaqueteId, ComponenteProductoId, Cantidad)
        SELECT @ProductoIdPaquete, ComponenteProductoId, SUM(Cantidad)
        FROM @Componentes
        GROUP BY ComponenteProductoId;   -- el TVP puede traer el mismo componente repetido

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'PAQUETE_ARMADO',
            @TablaAfectada = 'Repuestos.Paquetes', @RegistroId = @ProductoIdPaquete;

        SELECT CAST(1 AS BIT) AS Exito, 'Paquete armado correctamente' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPaquete;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
```

El `GROUP BY` en el `INSERT` final no está en el plan anterior y es el mismo problema de la clase B-4: sin él, el `UNIQUE (PaqueteId, ComponenteProductoId)` rechaza el lote entero si el usuario cargó dos veces el mismo componente, en vez de sumarlos.

### B.4 `Repuestos.sp_RegistrarVenta`

El SP más delicado del sistema. Incorpora las correcciones B-3, B-5 y B-6.

```sql
CREATE PROCEDURE Repuestos.sp_RegistrarVenta
    @UsuarioId      INT,
    @EsCredito      BIT = 0,
    @DiasCredito    INT = NULL,
    @Detalle        Repuestos.VentaDetalleTableType READONLY
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000;

    DECLARE @TranPropia BIT = 0;
    DECLARE @VentaId INT, @Subtotal DECIMAL(12,2), @MontoISV DECIMAL(12,2), @Total DECIMAL(12,2);
    DECLARE @Correlativo NVARCHAR(60), @MensajeCAI NVARCHAR(200), @ExitoCAI BIT;
    DECLARE @CodigoProblema NVARCHAR(30);

    DECLARE @StockRequerido TABLE (ProductoId INT PRIMARY KEY, CantidadRequerida INT NOT NULL);
    DECLARE @ResultadoCAI  TABLE (Exito BIT, Mensaje NVARCHAR(200), Correlativo NVARCHAR(60));

    BEGIN TRY
        ---------- 1. Validaciones previas, fuera de transacción ----------
        IF NOT EXISTS (SELECT 1 FROM @Detalle)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'La venta debe tener al menos un producto' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        IF EXISTS (SELECT 1 FROM @Detalle WHERE Cantidad <= 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay líneas con cantidad menor o igual a cero' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        -- DEFECTO B-6: producto inexistente o descontinuado
        IF EXISTS (SELECT 1 FROM @Detalle d
                   WHERE NOT EXISTS (SELECT 1 FROM Inventario.Productos p WHERE p.Id = d.ProductoId))
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Hay productos en la venta que no existen' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        SELECT TOP (1) @CodigoProblema = p.Codigo
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId
        WHERE p.Activo = 0;

        IF @CodigoProblema IS NOT NULL
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   CONCAT('El producto ', @CodigoProblema, ' está descontinuado y no puede venderse') AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        ---------- 2. Expandir paquetes a componentes reales ----------
        -- Lo que se factura es la línea comercial (el paquete);
        -- lo que se descuenta del inventario son sus componentes.
        INSERT INTO @StockRequerido (ProductoId, CantidadRequerida)
        SELECT ProductoId, SUM(CantidadRequerida)
        FROM (
            SELECT d.ProductoId, d.Cantidad AS CantidadRequerida
            FROM @Detalle d
            WHERE NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes pq WHERE pq.ProductoId = d.ProductoId)

            UNION ALL

            SELECT pd.ComponenteProductoId, pd.Cantidad * d.Cantidad
            FROM @Detalle d
            INNER JOIN Repuestos.PaqueteDetalle pd ON pd.PaqueteId = d.ProductoId
        ) expandido
        GROUP BY ProductoId;   -- un mismo componente puede venir de dos paquetes distintos

        ---------- 3. Chequeo previo de stock (filtro rápido, sin bloquear) ----------
        -- No es la validación definitiva: sirve para no gastar un correlativo CAI
        -- en una venta que ya se sabe condenada.
        IF EXISTS (SELECT 1 FROM @StockRequerido sr
                   INNER JOIN Inventario.Productos p ON p.Id = sr.ProductoId
                   WHERE p.StockActual < sr.CantidadRequerida)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Stock insuficiente para completar la venta' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        ---------- 4. Transacción ----------
        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoVenta;

        -- DEFECTO B-5: re-validar CON BLOQUEO. Sin esto, dos cajas simultáneas
        -- pasan ambas el chequeo del paso 3 y la segunda choca contra el
        -- CHECK (StockActual >= 0) con un error críptico.
        IF EXISTS (SELECT 1 FROM @StockRequerido sr
                   INNER JOIN Inventario.Productos p WITH (UPDLOCK) ON p.Id = sr.ProductoId
                   WHERE p.StockActual < sr.CantidadRequerida)
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVenta;
            SELECT CAST(0 AS BIT) AS Exito,
                   'Stock insuficiente: otra caja vendió el mismo producto' AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        ---------- 5. Correlativo CAI (Core) ----------
        INSERT INTO @ResultadoCAI (Exito, Mensaje, Correlativo)
            EXEC Facturacion.sp_ObtenerCorrelativoCAI;

        SELECT @ExitoCAI = Exito, @MensajeCAI = Mensaje, @Correlativo = Correlativo
        FROM @ResultadoCAI;

        IF @ExitoCAI = 0
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVenta;
            SELECT CAST(0 AS BIT) AS Exito, @MensajeCAI AS Mensaje,
                   CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
            RETURN;
        END

        ---------- 6. Montos sobre las LÍNEAS COMERCIALES ----------
        -- Se factura el paquete a su propio precio, no la suma de sus componentes.
        SELECT
            @Subtotal = SUM(d.Cantidad * p.PrecioUnitario),
            @MontoISV = SUM(Facturacion.fn_CalcularISV(d.Cantidad * p.PrecioUnitario, p.TasaISV))
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId;

        SET @Total = @Subtotal + @MontoISV;

        INSERT INTO Repuestos.Ventas (NumeroFactura, Subtotal, MontoISV, Total, UsuarioId, EsCredito)
        VALUES (@Correlativo, @Subtotal, @MontoISV, @Total, @UsuarioId, @EsCredito);

        SET @VentaId = SCOPE_IDENTITY();

        -- Precio y tasa se CONGELAN acá: una factura vieja nunca cambia de valor
        -- porque el producto haya cambiado de precio o de tasa después.
        INSERT INTO Repuestos.VentaDetalle (VentaId, ProductoId, Cantidad, PrecioUnitario, TasaISV)
        SELECT @VentaId, d.ProductoId, d.Cantidad, p.PrecioUnitario, p.TasaISV
        FROM @Detalle d
        INNER JOIN Inventario.Productos p ON p.Id = d.ProductoId;

        IF @EsCredito = 1
        BEGIN
            INSERT INTO Repuestos.CuentasPorCobrar (VentaId, MontoOriginal, SaldoPendiente, FechaVencimiento)
            VALUES (@VentaId, @Total, @Total,
                    DATEADD(DAY, ISNULL(@DiasCredito, 15), CAST(SYSDATETIME() AS DATE)));
        END

        ---------- 7. Descontar stock (una sola sentencia) ----------
        UPDATE p
        SET p.StockActual = p.StockActual - sr.CantidadRequerida
        FROM Inventario.Productos p
        INNER JOIN @StockRequerido sr ON sr.ProductoId = p.Id;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'VENTA_REGISTRADA',
            @TablaAfectada = 'Repuestos.Ventas', @RegistroId = @VentaId, @Detalle = @Correlativo;

        SELECT CAST(1 AS BIT) AS Exito, 'Venta registrada' AS Mensaje,
               @Correlativo AS NumeroFactura, @Total AS Total;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoVenta;
        END

        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje,
               CAST(NULL AS NVARCHAR(60)) AS NumeroFactura, CAST(NULL AS DECIMAL(12,2)) AS Total;
    END CATCH
END
GO
```

**Dos advertencias para quien lo implemente:**

- `INSERT ... EXEC` **no se puede anidar**. Como este SP usa `INSERT INTO @ResultadoCAI EXEC ...`, ningún otro SP puede a su vez llamar a `sp_RegistrarVenta` con `INSERT ... EXEC`. Desde C# con Dapper no hay problema; es una restricción para SPs futuros.
- El correlativo avanza dentro de la transacción de la venta. Si la venta falla después del paso 5, el rollback revierte también el avance y **el número se reutiliza en la siguiente venta**. Eso es deseable —no deja huecos en la numeración— pero es lo contrario de lo que afirmaba el plan anterior. Queda decidido así.

### B.5 `Repuestos.sp_AnularVenta`

Incorpora B-7 (vía D-3 opción c) y B-8 (vía D-4: rechazar mientras no haya regla).

```sql
CREATE PROCEDURE Repuestos.sp_AnularVenta
    @VentaId    INT,
    @UsuarioId  INT,
    @Motivo     NVARCHAR(200)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @TranPropia BIT = 0;
    DECLARE @StockDevuelto TABLE (ProductoId INT PRIMARY KEY, Cantidad INT NOT NULL);

    BEGIN TRY
        IF @Motivo IS NULL OR LEN(LTRIM(RTRIM(@Motivo))) = 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Debe indicar el motivo de la anulación' AS Mensaje;
            RETURN;
        END

        IF NOT EXISTS (SELECT 1 FROM Repuestos.Ventas WHERE Id = @VentaId AND Anulada = 0)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'Venta no encontrada o ya estaba anulada' AS Mensaje;
            RETURN;
        END

        -- DECISIÓN D-4 pendiente: mientras no exista la regla de negocio para
        -- devolver o acreditar el dinero ya recibido, no se permite anular.
        IF EXISTS (SELECT 1
                   FROM Repuestos.CuentasPorCobrar cxc
                   INNER JOIN Repuestos.PagoCuentaPorCobrar p ON p.CuentaPorCobrarId = cxc.Id
                   WHERE cxc.VentaId = @VentaId)
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito,
                   'Esta venta a crédito ya tiene pagos registrados y no puede anularse desde el sistema' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoAnulacion;

        -- Misma expansión que en la venta. Es correcta porque D-3 (c) prohíbe
        -- rearmar un paquete que ya tiene ventas: la composición no cambió.
        INSERT INTO @StockDevuelto (ProductoId, Cantidad)
        SELECT ProductoId, SUM(Cantidad)
        FROM (
            SELECT vd.ProductoId, vd.Cantidad
            FROM Repuestos.VentaDetalle vd
            WHERE vd.VentaId = @VentaId
              AND NOT EXISTS (SELECT 1 FROM Repuestos.Paquetes pq WHERE pq.ProductoId = vd.ProductoId)

            UNION ALL

            SELECT pd.ComponenteProductoId, pd.Cantidad * vd.Cantidad
            FROM Repuestos.VentaDetalle vd
            INNER JOIN Repuestos.PaqueteDetalle pd ON pd.PaqueteId = vd.ProductoId
            WHERE vd.VentaId = @VentaId
        ) expandido
        GROUP BY ProductoId;

        UPDATE p
        SET p.StockActual = p.StockActual + sd.Cantidad
        FROM Inventario.Productos p
        INNER JOIN @StockDevuelto sd ON sd.ProductoId = p.Id;

        -- La factura NUNCA se borra: el correlativo CAI ya fue emitido.
        UPDATE Repuestos.Ventas
        SET Anulada = 1, MotivoAnulacion = @Motivo, FechaAnulacion = SYSDATETIME()
        WHERE Id = @VentaId;

        -- Cerrar la cuenta por cobrar si existía y no tenía pagos (defecto B-8)
        UPDATE Repuestos.CuentasPorCobrar
        SET SaldoPendiente = 0, Estado = 'Anulada'
        WHERE VentaId = @VentaId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'VENTA_ANULADA',
            @TablaAfectada = 'Repuestos.Ventas', @RegistroId = @VentaId, @Detalle = @Motivo;

        SELECT CAST(1 AS BIT) AS Exito, 'Venta anulada, stock restaurado' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoAnulacion;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
```

### B.6 `Repuestos.sp_RegistrarPagoCuentaPorCobrar`

`sp_RegistrarPagoCuentaPorPagar` es idéntico cambiando tabla, columna (`CuentaPorPagarId`) y acción de auditoría a `'PAGO_CXP_REGISTRADO'`.

```sql
CREATE PROCEDURE Repuestos.sp_RegistrarPagoCuentaPorCobrar
    @CuentaPorCobrarId  INT,
    @Monto              DECIMAL(12,2),
    @MetodoPago         NVARCHAR(30) = NULL,
    @UsuarioId          INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET LOCK_TIMEOUT 5000;

    DECLARE @TranPropia BIT = 0;
    DECLARE @SaldoActual DECIMAL(12,2), @Estado NVARCHAR(20);

    BEGIN TRY
        IF @Monto IS NULL OR @Monto <= 0
        BEGIN
            SELECT CAST(0 AS BIT) AS Exito, 'El monto del pago debe ser mayor a cero' AS Mensaje;
            RETURN;
        END

        IF @@TRANCOUNT = 0
        BEGIN
            BEGIN TRAN;
            SET @TranPropia = 1;
        END
        ELSE
            SAVE TRANSACTION PuntoPago;

        -- UPDLOCK: la lectura del saldo y su actualización deben ser atómicas.
        SELECT @SaldoActual = SaldoPendiente, @Estado = Estado
        FROM Repuestos.CuentasPorCobrar WITH (UPDLOCK)
        WHERE Id = @CuentaPorCobrarId;

        IF @SaldoActual IS NULL
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
            SELECT CAST(0 AS BIT) AS Exito, 'Cuenta por cobrar no encontrada' AS Mensaje;
            RETURN;
        END

        IF @Estado = 'Anulada'
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
            SELECT CAST(0 AS BIT) AS Exito, 'La cuenta corresponde a una venta anulada' AS Mensaje;
            RETURN;
        END

        IF @Monto > @SaldoActual
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
            SELECT CAST(0 AS BIT) AS Exito, 'El pago excede el saldo pendiente' AS Mensaje;
            RETURN;
        END

        INSERT INTO Repuestos.PagoCuentaPorCobrar (CuentaPorCobrarId, Monto, MetodoPago, UsuarioId)
        VALUES (@CuentaPorCobrarId, @Monto, @MetodoPago, @UsuarioId);

        UPDATE Repuestos.CuentasPorCobrar
        SET SaldoPendiente = SaldoPendiente - @Monto,
            Estado = CASE WHEN SaldoPendiente - @Monto = 0 THEN 'Pagada' ELSE 'PagadaParcial' END
        WHERE Id = @CuentaPorCobrarId;

        IF @TranPropia = 1 COMMIT;

        EXEC Auditoria.sp_RegistrarAuditoria
            @UsuarioId = @UsuarioId, @Accion = 'PAGO_CXC_REGISTRADO',
            @TablaAfectada = 'Repuestos.CuentasPorCobrar', @RegistroId = @CuentaPorCobrarId;

        SELECT CAST(1 AS BIT) AS Exito, 'Pago registrado' AS Mensaje;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() = -1 ROLLBACK;
        ELSE IF XACT_STATE() = 1
        BEGIN
            IF @TranPropia = 1 ROLLBACK; ELSE ROLLBACK TRANSACTION PuntoPago;
        END
        SELECT CAST(0 AS BIT) AS Exito, ERROR_MESSAGE() AS Mensaje;
    END CATCH
END
GO
```

### B.7 `Inventario.sp_ListarProductos` — paginado (tarea 4.7)

Patrón a copiar en **todos** los listados del sistema.

```sql
CREATE PROCEDURE Inventario.sp_ListarProductos
    @SoloActivos    BIT = 1,
    @CategoriaId    INT = NULL,
    @Busqueda       NVARCHAR(150) = NULL,
    @Pagina         INT = 1,
    @TamanoPagina   INT = 50
AS
BEGIN
    SET NOCOUNT ON;

    IF @Pagina < 1 SET @Pagina = 1;
    IF @TamanoPagina < 1 OR @TamanoPagina > 500 SET @TamanoPagina = 50;

    -- Result set 1: la página
    SELECT
        p.Id, p.Codigo, p.Nombre, p.Descripcion, p.PrecioUnitario,
        p.CategoriaId, c.Nombre AS NombreCategoria,
        p.TasaISV, p.StockActual, p.StockMinimo, p.Activo, p.FechaCreacion
    FROM Inventario.Productos p
    LEFT JOIN Inventario.Categorias c ON p.CategoriaId = c.Id
    WHERE (@SoloActivos = 0 OR p.Activo = 1)
      AND (@CategoriaId IS NULL OR p.CategoriaId = @CategoriaId)
      AND (@Busqueda IS NULL OR p.Codigo LIKE '%' + @Busqueda + '%'
                             OR p.Nombre LIKE '%' + @Busqueda + '%')
    ORDER BY p.Nombre
    OFFSET (@Pagina - 1) * @TamanoPagina ROWS
    FETCH NEXT @TamanoPagina ROWS ONLY
    OPTION (RECOMPILE);

    -- Result set 2: total para calcular el número de páginas
    SELECT COUNT(*) AS TotalFilas
    FROM Inventario.Productos p
    WHERE (@SoloActivos = 0 OR p.Activo = 1)
      AND (@CategoriaId IS NULL OR p.CategoriaId = @CategoriaId)
      AND (@Busqueda IS NULL OR p.Codigo LIKE '%' + @Busqueda + '%'
                             OR p.Nombre LIKE '%' + @Busqueda + '%')
    OPTION (RECOMPILE);
END
GO
```

Notar que `@SoloActivos = 0` significa **"traer todos"**, no "solo inactivos". El nombre del parámetro engaña y viene del código original; se conserva por compatibilidad, pero queda documentado acá.

`OPTION (RECOMPILE)` es lo que evita que el plan generado para "buscar por categoría" se reutilice para "listar todo" (*parameter sniffing*). En una consulta interactiva, recompilar cuesta milisegundos.

### B.8 `Auditoria.sp_PurgarAuditoria` (tarea 4.11)

```sql
CREATE PROCEDURE Auditoria.sp_PurgarAuditoria
    @DiasAConservar INT = 365
AS
BEGIN
    SET NOCOUNT ON;

    IF @DiasAConservar < 90 SET @DiasAConservar = 90;   -- piso de seguridad

    DECLARE @Corte DATETIME2(0) = DATEADD(DAY, -@DiasAConservar, SYSDATETIME());
    DECLARE @Borradas INT = 1, @Total INT = 0;

    -- Lotes chicos: un DELETE masivo escala el bloqueo a nivel de tabla y
    -- congela el sistema entero. En lotes, cada transacción es corta y las
    -- demás sesiones siguen trabajando.
    WHILE @Borradas > 0
    BEGIN
        DELETE TOP (5000) FROM Auditoria.Auditoria WHERE FechaHora < @Corte;
        SET @Borradas = @@ROWCOUNT;
        SET @Total = @Total + @Borradas;

        IF @Borradas > 0 WAITFOR DELAY '00:00:00.100';
    END

    SELECT CAST(1 AS BIT) AS Exito,
           CONCAT('Purga completada: ', @Total, ' registros eliminados') AS Mensaje,
           @Total AS FilasEliminadas;
END
GO
```

Lo dispara `Sistemas.Mantenimiento`, **no** un job del Agent: SQL Server Express no incluye SQL Server Agent.

---

## Anexo C — Manifiesto de archivos y `.sqlproj`

### C.1 Cambios en `Sistemas.Core.Database`

| Archivo | Acción | Referencia |
|---|---|---|
| `Security/Tables/Roles.sql` | **Agregar al `.sqlproj`** (el archivo ya existe) | A-1 |
| `Security/Tables/Usuarios.sql` | **Agregar al `.sqlproj`** (el archivo ya existe) | A-1 |
| `Security/StoredProcedures/sp_Login.sql` | **Borrar** archivo y entrada del `.sqlproj` | B-1 |
| `Configuracion/Tables/Configuracion.sql` | Reemplazar contenido | Anexo A.1 |
| `Configuracion/Tables/VersionEsquema.sql` | Crear | Anexo A.1 |
| `Configuracion/StoredProcedures/sp_GuardarConfiguracion.sql` | Editar: quitar `SET IDENTITY_INSERT`, insertar `Id = 1` literal, mover auditoría después del `COMMIT` | B-2, B-9 |
| `Configuracion/StoredProcedures/sp_ObtenerLogo.sql` | Crear | tarea 4.10 |
| `Configuracion/StoredProcedures/sp_VerificarEstadoSistema.sql` | Crear | sección 7 |
| `Inventario/Tables/Productos.sql` | Editar: quitar `IX_Productos_Activo`, agregar `IX_Productos_Activo_Nombre` | C-2 |
| `Inventario/StoredProcedures/sp_ListarProductos.sql` | Reemplazar contenido | Anexo B.7 |
| `Inventario/StoredProcedures/sp_CrearCategoria.sql` | Editar: validación anti-ciclo con CTE recursivo; auditoría después del `COMMIT` | B-10, B-9 |
| `Inventario/StoredProcedures/sp_CrearProducto.sql` | Editar: auditoría después del `COMMIT` | B-9 |
| `Inventario/StoredProcedures/sp_AsignarEtiqueta.sql` | Editar: auditoría después del `COMMIT` | B-9 |
| `Facturacion/Functions/fn_CalcularISV.sql` | Editar: `WITH SCHEMABINDING` | Anexo A.1 |
| `Facturacion/StoredProcedures/sp_ObtenerCorrelativoCAI.sql` | Reemplazar contenido | Anexo B.1 |
| `Auditoria/StoredProcedures/sp_PurgarAuditoria.sql` | Crear | Anexo B.8 |

`sp_ObtenerCredencialesLogin` y `sp_RegistrarResultadoLogin` **no se tocan**: están correctos.

**`ItemGroup` de `Build` completo para `Sistemas.Core.Database.sqlproj`** (reemplaza el actual):

```xml
<ItemGroup>
  <Build Include="Auditoria\Auditoria.sql" />
  <Build Include="Auditoria\Tables\Auditoria.sql" />
  <Build Include="Auditoria\StoredProcedures\sp_RegistrarAuditoria.sql" />
  <Build Include="Auditoria\StoredProcedures\sp_PurgarAuditoria.sql" />
  <Build Include="Configuracion\Configuracion.sql" />
  <Build Include="Configuracion\Tables\Configuracion.sql" />
  <Build Include="Configuracion\Tables\VersionEsquema.sql" />
  <Build Include="Configuracion\StoredProcedures\sp_GuardarConfiguracion.sql" />
  <Build Include="Configuracion\StoredProcedures\sp_ObtenerLogo.sql" />
  <Build Include="Configuracion\StoredProcedures\sp_VerificarEstadoSistema.sql" />
  <Build Include="Facturacion\Facturacion.sql" />
  <Build Include="Facturacion\Tables\ConfiguracionCAI.sql" />
  <Build Include="Facturacion\Functions\fn_CalcularISV.sql" />
  <Build Include="Facturacion\StoredProcedures\sp_ObtenerCorrelativoCAI.sql" />
  <Build Include="Inventario\Inventario.sql" />
  <Build Include="Inventario\Tables\Categorias.sql" />
  <Build Include="Inventario\Tables\Etiquetas.sql" />
  <Build Include="Inventario\Tables\Productos.sql" />
  <Build Include="Inventario\Tables\ProductoEtiqueta.sql" />
  <Build Include="Inventario\Types\ProductoTableType.sql" />
  <Build Include="Inventario\StoredProcedures\sp_CrearProducto.sql" />
  <Build Include="Inventario\StoredProcedures\sp_CrearCategoria.sql" />
  <Build Include="Inventario\StoredProcedures\sp_AsignarEtiqueta.sql" />
  <Build Include="Inventario\StoredProcedures\sp_ListarProductos.sql" />
  <Build Include="Inventario\StoredProcedures\sp_ImportarProductosMasivo.sql" />
  <Build Include="Security\Security.sql" />
  <Build Include="Security\Tables\Roles.sql" />
  <Build Include="Security\Tables\Usuarios.sql" />
  <Build Include="Security\StoredProcedures\sp_ObtenerCredencialesLogin.sql" />
  <Build Include="Security\StoredProcedures\sp_RegistrarResultadoLogin.sql" />
</ItemGroup>
```

Las dos líneas que faltaban son `Security\Tables\Roles.sql` y `Security\Tables\Usuarios.sql`; `sp_Login.sql` ya no aparece.

### C.2 Archivos de `Sistemas.Repuestos.Database`

Los 15 archivos existentes están en 0 bytes: hay que llenarlos, no crearlos de nuevo (salvo donde diga *crear*).

**Fase 1 — catálogo**
- `Repuestos/Repuestos.sql` — ya tiene `CREATE SCHEMA Repuestos;`, no tocar
- `Repuestos/Tables/DetalleProducto.sql` — **crear** (fue borrado del working tree)
- `Repuestos/Tables/VehiculoCompatible.sql` — llenar
- `Repuestos/Tables/NumeroEquivalente.sql` — llenar
- `Repuestos/StoredProcedures/sp_GuardarDetalleProducto.sql` — crear
- `Repuestos/StoredProcedures/sp_AgregarVehiculoCompatible.sql` — crear
- `Repuestos/StoredProcedures/sp_AgregarNumeroEquivalente.sql` — crear
- `Repuestos/StoredProcedures/sp_BuscarPorEquivalencia.sql` — crear

**Fase 2 — proveedores**
- `Repuestos/Tables/Proveedores.sql` — llenar
- `Repuestos/Tables/ProductoProveedor.sql` — llenar
- `Repuestos/StoredProcedures/sp_GuardarProveedor.sql` — crear
- `Repuestos/StoredProcedures/sp_ListarProveedores.sql` — crear
- `Repuestos/StoredProcedures/sp_GuardarPrecioProveedor.sql` — crear
- `Repuestos/StoredProcedures/sp_CompararPreciosProveedor.sql` — crear

**Fase 3 — compras**
- `Repuestos/Tables/Compras.sql` — **mover** desde `Repuestos/Compras/Compras.sql` y llenar; borrar la carpeta `Compras/`
- `Repuestos/Tables/CompraDetalle.sql` — crear
- `Repuestos/Types/CompraDetalleTableType.sql` — llenar
- `Repuestos/StoredProcedures/sp_RegistrarCompra.sql` — llenar (Anexo B.2)

**Fase 4 — paquetes**
- `Repuestos/Tables/Paquetes.sql` — llenar
- `Repuestos/Tables/PaqueteDetalle.sql` — llenar
- `Repuestos/Types/PaqueteDetalleTableType.sql` — crear
- `Repuestos/StoredProcedures/sp_ArmarPaquete.sql` — crear (Anexo B.3)

**Fase 5 — ventas**
- `Repuestos/Tables/Ventas.sql` — llenar
- `Repuestos/Tables/VentaDetalle.sql` — llenar
- `Repuestos/Types/VentaDetalleTableType.sql` — crear
- `Repuestos/StoredProcedures/sp_RegistrarVenta.sql` — llenar (Anexo B.4)
- `Repuestos/StoredProcedures/sp_AnularVenta.sql` — llenar (Anexo B.5)
- `Repuestos/StoredProcedures/sp_ObtenerProductoRepuesto.sql` — llenar

**Fase 6 — cuentas**
- `Repuestos/Tables/CuentasPorCobrar.sql` — llenar
- `Repuestos/Tables/PagoCuentaPorCobrar.sql` — crear
- `Repuestos/Tables/CuentasPorPagar.sql` — crear
- `Repuestos/Tables/PagoCuentaPorPagar.sql` — crear
- `Repuestos/StoredProcedures/sp_RegistrarPagoCuentaPorCobrar.sql` — crear (Anexo B.6)
- `Repuestos/StoredProcedures/sp_RegistrarPagoCuentaPorPagar.sql` — crear
- `Repuestos/StoredProcedures/sp_ListarCuentasPorCobrar.sql` — crear
- `Repuestos/StoredProcedures/sp_ListarCuentasPorPagar.sql` — crear

**`ItemGroup` de `Build` completo para `Sistemas.Repuestos.Database.sqlproj`** (reemplaza el que está sin commitear, cuyas rutas son incorrectas):

```xml
<ItemGroup>
  <Build Include="Repuestos\Repuestos.sql" />
  <Build Include="Repuestos\Tables\DetalleProducto.sql" />
  <Build Include="Repuestos\Tables\VehiculoCompatible.sql" />
  <Build Include="Repuestos\Tables\NumeroEquivalente.sql" />
  <Build Include="Repuestos\Tables\Proveedores.sql" />
  <Build Include="Repuestos\Tables\ProductoProveedor.sql" />
  <Build Include="Repuestos\Tables\Compras.sql" />
  <Build Include="Repuestos\Tables\CompraDetalle.sql" />
  <Build Include="Repuestos\Tables\Paquetes.sql" />
  <Build Include="Repuestos\Tables\PaqueteDetalle.sql" />
  <Build Include="Repuestos\Tables\Ventas.sql" />
  <Build Include="Repuestos\Tables\VentaDetalle.sql" />
  <Build Include="Repuestos\Tables\CuentasPorCobrar.sql" />
  <Build Include="Repuestos\Tables\PagoCuentaPorCobrar.sql" />
  <Build Include="Repuestos\Tables\CuentasPorPagar.sql" />
  <Build Include="Repuestos\Tables\PagoCuentaPorPagar.sql" />
  <Build Include="Repuestos\Types\CompraDetalleTableType.sql" />
  <Build Include="Repuestos\Types\PaqueteDetalleTableType.sql" />
  <Build Include="Repuestos\Types\VentaDetalleTableType.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_GuardarDetalleProducto.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_AgregarVehiculoCompatible.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_AgregarNumeroEquivalente.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_BuscarPorEquivalencia.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_GuardarProveedor.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_ListarProveedores.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_GuardarPrecioProveedor.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_CompararPreciosProveedor.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_RegistrarCompra.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_ArmarPaquete.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_RegistrarVenta.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_AnularVenta.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_ObtenerProductoRepuesto.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_RegistrarPagoCuentaPorCobrar.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_RegistrarPagoCuentaPorPagar.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_ListarCuentasPorCobrar.sql" />
  <Build Include="Repuestos\StoredProcedures\sp_ListarCuentasPorPagar.sql" />
</ItemGroup>
```

La `ProjectReference` hacia `Sistemas.Core.Database` que ya está en el `.sqlproj` es correcta y no se toca: es la que hace visibles `Inventario.Productos`, `Security.Usuarios` y `Facturacion.ConfiguracionCAI` desde este proyecto.

### C.3 Criterio de terminado por fase

Una fase está cerrada cuando se cumplen las tres condiciones:

1. **Compila.** El `.sqlproj` construye sin errores ni advertencias de referencias no resueltas.
2. **Despliega en limpio.** Publicar contra una base vacía funciona de punta a punta, incluido el script post-despliegue con los datos semilla.
3. **Pasa sus pruebas.** Los escenarios de la sección 9 que corresponden a esa fase se ejecutan y dan el resultado esperado.

Mapa de pruebas por fase: Fase 3 → prueba 4. Fase 4 → prueba 1. Fase 5 → pruebas 1, 2, 3, 5, 6, 10. Fase 6 → prueba 7. Fase 0 → pruebas 8 y 9.

### C.4 Lo que este documento deliberadamente no especifica

Para que quien implemente sepa dónde **sí** tiene que preguntar en vez de decidir solo:

- Los cuerpos de los SP mecánicos de las fases 1, 2 y 6 (altas, ediciones, listados). Se derivan de la plantilla C-5 y el contrato C-4.
- El contenido del script post-despliegue más allá de los roles semilla y la fila de `VersionEsquema`.
- Cualquier cosa que dependa de `D-1` a `D-6` de la sección 10. Donde un anexo asumió una decisión, lo dice en el propio texto.
- El proyecto `Sistemas.Mantenimiento`: es C#, queda fuera del alcance de este documento salvo por las operaciones SQL que debe disparar (sección 7).
