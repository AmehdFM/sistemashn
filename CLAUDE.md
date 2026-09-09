# CLAUDE.md — Contexto obligatorio para asistentes de IA

> **Leé este archivo completo antes de escribir una sola línea de código.**
> Está escrito para que un asistente sin contexto previo pueda trabajar en
> este repositorio sin volver a deducir decisiones que ya están tomadas.

---

## 1. Qué es este proyecto en una frase

**SistemasHN** es un sistema empresarial (ERP/POS) de **escritorio Windows**,
**100 % offline**, para la **pequeña y mediana empresa hondureña**, construido
sobre una arquitectura de **núcleo compartido + verticales por rubro**. La
primera vertical es **autorepuestos**; la siguiente prevista es **ferretería /
materiales de construcción**.

- **Stack:** .NET 10 · WinForms · SQL Server Express · Dapper · SSDT (`.sqlproj`)
- **Idioma de TODO:** español (código, comentarios, commits, UI, documentación)
- **Modelo de negocio:** licencia perpetua por máquina, activación offline firmada
- **Estado:** en desarrollo — **no hay ningún cliente en producción todavía**

---

## 2. Las restricciones que explican todas las decisiones

Nada de lo que sigue es preferencia estética. Cada regla de este repositorio
sale de una de estas siete restricciones del cliente real:

| Restricción del cliente | Lo que obliga |
|---|---|
| **Sin internet** | Cero dependencias en línea. Ni telemetría, ni CDN, ni validación de licencia por red, ni actualizaciones automáticas. El reloj es el de la máquina: `SYSDATETIME()`, nunca `GETUTCDATE()`. |
| **Cortes de energía frecuentes** | Durabilidad innegociable. **Prohibido `DELAYED_DURABILITY`.** Toda operación de dinero o inventario es una transacción atómica. El respaldo automático es parte del producto, no una comodidad. |
| **PC de bajos recursos** | SQL Express usa 1 GB de buffer pool. **Todo listado va paginado en el servidor.** Nada de traer tablas completas a la pantalla. Cada índice se justifica; ninguno "por si acaso". |
| **Base de 10 GB máximo (Express)** | `Auditoria.Auditoria` es la única tabla que crece sin techo: necesita purga por antigüedad desde el día uno. |
| **Sin personal técnico en el sitio** | Ningún error crudo de SQL Server llega a la pantalla. Todo SP devuelve `Exito`/`Mensaje` en español. Los detalles técnicos van a auditoría. |
| **Muchos clientes, cada uno con su copia** | Versionado de esquema y actualización por DACPAC. Actualizar 30 instalaciones offline a mano es inviable. |
| **Español de Honduras** | ISV 15 % (0 % exento, 18 % especial), facturación CAI del SAR, lempiras, formato `N2`. Ver la decisión abierta sobre collation acento-insensitiva (ADR-0016). |

---

## 3. Reglas duras — nunca las rompas sin autorización explícita

Estas cuatro no se negocian en una sesión de trabajo. Si una tarea parece
exigir romperlas, **detenete y preguntá** en vez de improvisar.

### R1 — Toda regla de negocio vive en el stored procedure
La app **nunca** asume que validó. Un SP debe ser correcto aunque alguien se
conecte con SSMS y lo llame a mano. C# orquesta y presenta; SQL decide.
Excepción única y documentada: la verificación de contraseña con BCrypt ocurre
en C# (ADR-0012).

### R2 — Core nunca conoce una vertical
`Sistemas.Core` y `Sistemas.Core.UI` **jamás** referencian un tipo de
`Sistemas.Repuestos.*`. Toda extensión pasa por `IVerticalModuleProvider` e
`IDashboardModule`. Si algo de una vertical "necesita" entrar a Core, o se
generaliza sin nombrar la vertical, o no entra.
En la base de datos el equivalente es **C-2**: una vertical referencia Core por
FK y nada más — ni un `ALTER TABLE` sobre `Inventario.Productos`.

### R3 — Ningún texto ni color suelto
- Todo string visible para el usuario vive en un `Textos.cs`:
  `Sistemas.Core/Textos.cs` (negocio compartido) ·
  `Sistemas.Core.UI/Textos.cs` (pantallas compartidas) ·
  `Sistemas.Repuestos.Library/Textos.cs` (esa vertical).
- Todo color y fuente vive en `Sistemas.Core.UI/UiTheme.cs`. Ningún
  `Color.FromArgb` ni `new Font(...)` suelto en una pantalla.

### R4 — Sin dependencias nuevas sin aprobación
No agregues paquetes NuGet, servicios externos ni herramientas. El entorno es
offline y cada dependencia es peso en una máquina que no lo tiene. Las
dependencias actuales están listadas en `docs/01-arquitectura.md` §5.

**Además:** las convenciones **C-1 a C-9** de base de datos
(`docs/03-convenciones-base-datos.md`) son obligatorias para todo objeto SQL
nuevo, muy en especial la **plantilla C-5** de transacción anidada.

---

## 4. Antes de empezar cualquier tarea

1. **Identificá la capa.** ¿SQL, negocio (`Sistemas.Core` / `*.Library/Services`),
   o UI? Cada capa tiene su documento de convenciones.
2. **Buscá el precedente.** Casi todo lo que vas a escribir ya tiene un gemelo
   en el repositorio. Copiá su estructura antes de inventar una nueva:
   - SP que muta datos → `Repuestos/StoredProcedures/sp_RegistrarCompra.sql`
   - SP de listado paginado → `Inventario/StoredProcedures/sp_ListarProductos.sql`
   - Servicio de datos → `Sistemas.Core/Inventory/ProductService.cs`
   - Pantalla de listado → `Sistemas.Repuestos.Library/Proveedores/ProveedoresControl.cs`
   - Módulo de dashboard → `Sistemas.Repuestos.Library/Dashboard/ComprasDashboardModule.cs`
3. **Consultá la decisión, no la reinventes.** `docs/decisiones/` tiene el
   porqué de cada elección estructural. Si tu tarea contradice un ADR, decilo
   antes de implementar.
4. **Si la respuesta no está escrita, preguntá.** Especialmente en las
   decisiones abiertas (ADR-0016 a ADR-0021): collation, estrategia de
   búsqueda, paquetes históricos, anulación a crédito, procedimiento SAR y
   versión mínima de SQL Server. **Ninguna se resuelve por cuenta propia.**

---

## 5. Mapa de la documentación

| Documento | Cuándo leerlo |
|---|---|
| `docs/00-producto-y-mercado.md` | Para entender a quién le vendemos y por qué el producto es así |
| `docs/01-arquitectura.md` | Antes de crear un proyecto, una capa o un módulo nuevo |
| `docs/02-convenciones-codigo.md` | Antes de escribir C# |
| `docs/03-convenciones-base-datos.md` | Antes de escribir SQL — **incluye las plantillas obligatorias** |
| `docs/04-dominio-y-glosario.md` | Cuando no sepas qué significa un término del negocio o dónde vive un dato |
| `docs/05-estado-y-roadmap.md` | Para saber qué está hecho de verdad y qué es un stub |
| `docs/06-despliegue-y-operacion.md` | Instalación, actualización, respaldo, licenciamiento |
| `docs/07-estrategia-de-pruebas.md` | Cómo se verifica un cambio hoy (no hay tests automatizados) |
| `docs/08-flujo-de-trabajo-con-ia.md` | **Cómo trabajar en este repo como IA** — criterios de terminado |
| `docs/decisiones/` | El porqué de cada decisión estructural (ADRs) |
| `plan-desarrollo-base-datos.md` | Plan de referencia con el DDL exacto y los cuerpos de SP |
| `GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md` | Guía de diseño visual y de interacción — **manda en toda pantalla nueva** |

> **Jerarquía ante conflicto:** este `CLAUDE.md` → los ADRs →
> `plan-desarrollo-base-datos.md` (sus anexos mandan sobre su prosa) →
> `GUIA-UI-UX-...md` → el código existente. Si encontrás una contradicción
> real, reportala en vez de elegir en silencio.

---

## 6. Compilar y ejecutar

```bash
dotnet build SistemasHN.slnx          # compila todo (requiere Windows para los .sqlproj)
dotnet run --project Sistemas.Repuestos   # arranca la vertical de autorepuestos
```

- El `.slnx` es el formato nuevo de solución; no lo conviertas a `.sln`.
- Los proyectos `.sqlproj` (SSDT) **solo compilan en Windows con Visual Studio
  o los SDK de SSDT**. En Linux/CI se editan y revisan los `.sql`, no se
  construye el DACPAC.
- El connection string se busca primero en
  `%ProgramData%\SistemasHN\appsettings.json` y, si no existe, junto al `.exe`.
  En desarrollo alcanza con `Sistemas.Repuestos/appsettings.json`.

---

## 7. Convenciones de trabajo con git

- Rama de integración: `desarrollo`. No se trabaja directo sobre ella.
- Commits en **español**, en imperativo o sustantivado, describiendo el cambio
  de negocio y no el archivo tocado. Ejemplo real del historial:
  `Unidades de medida, cantidades decimales y rediseno de Inventario a maestro-detalle`.
- **Nunca** subas `Sistemas.Licencias/clave_privada.pem` ni ninguna clave
  privada. Es el secreto más importante del sistema: sin ella no se pueden
  emitir activaciones nuevas, y con ella cualquiera puede piratear el producto.

---

## 8. Errores que ya se cometieron — no los repitas

Estos salieron de revisiones reales de este código. Están documentados en
detalle en `plan-desarrollo-base-datos.md` §3.

- **Devolver `NULL` a secas en un SP.** Dapper mapea la columna como `int` y
  revienta. Siempre `CAST(NULL AS <tipo>)` explícito.
- **`ROLLBACK` a secas dentro de un SP anidado.** Revierte la transacción del
  llamador y provoca el error 3903. Usá la plantilla C-5, siempre.
- **Validar stock fuera de la transacción y confiar en eso.** Es una condición
  de carrera entre dos cajas. Se revalida **con bloqueo** dentro de la
  transacción.
- **`UPDATE ... FROM ... JOIN` contra un TVP sin agrupar.** Si el TVP trae el
  mismo `ProductoId` dos veces, aplica una sola coincidencia **en silencio**.
- **Declarar una FK y no crear su índice.** SQL Server no lo crea solo.
- **Índice sobre un `BIT` con 95 % de un valor.** No aporta selectividad; el
  optimizador hace scan igual. Usá índices filtrados que cubran la consulta.
- **Bloquear el hilo de UI con `.GetAwaiter().GetResult()`.** Interbloqueo
  permanente en WinForms. Ver la nota en `AppBootstrapper.cs`.
