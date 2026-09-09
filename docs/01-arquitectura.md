# 01 — Arquitectura

## 1. La idea en una imagen

```
                      ┌──────────────────────────────────┐
                      │   Sistemas.Repuestos  (.exe)     │  ← raíz de composición
                      │   Program.cs: registra módulos   │     una por vertical
                      └───────────────┬──────────────────┘
                                      │
            ┌─────────────────────────┼──────────────────────────┐
            ▼                         ▼                          ▼
┌───────────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│ Sistemas.Core.UI      │  │ Sistemas.Core      │  │ Sistemas.Repuestos.      │
│ shell, arranque,      │  │ servicios de       │  │ Library                  │
│ tema, contratos de    │  │ negocio comunes,   │  │ pantallas + servicios    │
│ módulo                │  │ datos, licencias   │  │ de la vertical           │
└──────────┬────────────┘  └─────────┬──────────┘  └────────────┬─────────────┘
           └───────────────────┬─────┘                          │
                               ▼                                ▼
                    ┌──────────────────────────────────────────────────┐
                    │        SQL Server Express — base SistemasHN      │
                    │  Core:      Security · Configuracion · Auditoria │
                    │             Inventario · Facturacion             │
                    │  Vertical:  Repuestos                            │
                    └──────────────────────────────────────────────────┘
```

**Regla de oro:** las flechas nunca apuntan hacia arriba. `Sistemas.Core` y
`Sistemas.Core.UI` no conocen ni pueden conocer a `Sistemas.Repuestos.*`.

## 2. Los proyectos

| Proyecto | Target | Qué es | Depende de |
|---|---|---|---|
| `Sistemas.Core` | `net10.0` | Lógica de negocio y acceso a datos compartidos. **Sin WinForms**: se puede consumir desde una consola o un servicio. | — |
| `Sistemas.Core.UI` | `net10.0-windows` | Shell visual compartido: arranque, dashboard, tema, contratos de módulo, controles comunes. | `Sistemas.Core` |
| `Sistemas.Core.Database` | SSDT | Esquemas `Security`, `Configuracion`, `Auditoria`, `Inventario`, `Facturacion`. | — |
| `Sistemas.Repuestos.Library` | `net10.0-windows` | Toda la vertical de autorepuestos: pantallas, servicios, DTOs, módulos de dashboard. | `Core`, `Core.UI` |
| `Sistemas.Repuestos.Database` | SSDT | Esquema `Repuestos`. Referencia a Core por FK; **nunca lo modifica**. | Core.Database (por FK) |
| `Sistemas.Repuestos` | `net10.0-windows` · WinExe | El ejecutable. Es solo raíz de composición: fija cultura, registra módulos, corre el bucle sesión. | `Core`, `Core.UI`, `Repuestos.Library` |
| `Sistemas.Mantenimiento` | `net10.0` · Exe | Respaldo, purga y verificación de integridad. **Hoy es un stub.** | `Sistemas.Core` |
| `Sistemas.Licencias` | `net10.0-windows` · Exe | Generador de claves de activación. **Herramienta interna del vendedor**, no se distribuye. | — |

## 3. Las capas dentro de una vertical

```
Pantalla (UserControl / Form)      ← WinForms. Solo presentación y captura.
        ↓
Servicio (*Service.cs)             ← Estático. Abre conexión, llama al SP, mapea con Dapper.
        ↓
DTO (*Dto.cs)                      ← Contrato de datos. Sin lógica.
        ↓
Stored procedure                   ← Aquí vive TODA la regla de negocio.
```

**Por qué el servicio es delgado a propósito:** si la regla estuviera en C#,
alguien conectándose con SSMS podría dejar la base inconsistente, y la lógica
habría que reescribirla el día que la UI cambie. Ver [ADR-0002](decisiones/ADR-0002-logica-de-negocio-en-stored-procedures.md).

## 4. El flujo de arranque

`Sistemas.Repuestos/Program.cs` hace exactamente cuatro cosas, en este orden:

1. **Fija la cultura** a `en-US` en `DefaultThreadCurrentCulture`, para que el
   punto decimal y la coma de miles no dependan del Windows de cada cliente
   ([ADR-0008](decisiones/ADR-0008-cultura-fija-en-el-arranque.md)).
2. **Registra los módulos base de Core** (`Menú`, `Ajustes`) y luego los de la
   vertical vía `new RepuestosModuleProvider().RegistrarModulos()`. Una sola
   vez: el registro no depende de la sesión y repetirlo duplicaría entradas.
3. **Corre `AppBootstrapper.EjecutarHastaLogin()`**, que dentro de una única
   `FormArranque` encadena los pasos que hagan falta:
   `Activación de licencia → Primer usuario → Datos del negocio → Login`.
   Cada paso es un `UserControl` que solo avanza al disparar su evento de éxito.
4. **Abre `FormDashboardBase`** y entra en bucle: si el dashboard devuelve
   `DialogResult.Retry`, el usuario cerró sesión y se vuelve al arranque.

Cambiar de vertical significa cambiar **una línea** de este archivo: qué
`IVerticalModuleProvider` se instancia.

## 5. Dependencias externas

Todas viven en `Sistemas.Core`. Ninguna se agrega sin autorización explícita
(regla R4 de `CLAUDE.md`).

| Paquete | Versión | Para qué | Por qué esa y no otra |
|---|---|---|---|
| `Dapper` | 2.1.79 | Mapeo de resultados de SP a DTO | Micro-ORM: no genera SQL, que es justo lo que queremos ([ADR-0003](decisiones/ADR-0003-dapper-en-vez-de-ef-core.md)) |
| `Microsoft.Data.SqlClient` | 7.0.2 | Conexión a SQL Server | Cliente oficial y mantenido |
| `BCrypt.Net-Next` | 4.0.3 | Hash y verificación de contraseñas | Algoritmo con costo ajustable; SQL Server no tiene equivalente |
| `ClosedXML` | 0.105.1 | Exportar e importar Excel | Sin dependencia de Office instalado |
| `Serilog` + `Serilog.Sinks.File` | 4.4.0 / 7.0.0 | Log a archivo | **Referenciado pero sin configurar todavía** — `LoggerConfig.cs` es un stub |
| `System.Management` | 8.0.0 | WMI para el fingerprint de máquina | Única forma de leer serie de CPU/disco/placa |
| `System.Security.Cryptography.ProtectedData` | 9.0.13 | DPAPI para guardar la licencia | Cifrado atado a la máquina, sin gestionar llaves |

## 6. Cómo se extiende: agregar una vertical nueva

Este es el camino completo. Ninguno de estos pasos toca Core.

1. **Proyecto de base de datos** `Sistemas.<Rubro>.Database` con su propio
   esquema. Referencia a Core por FK; nunca un `ALTER TABLE` sobre Core (C-2).
2. **Proyecto de librería** `Sistemas.<Rubro>.Library` (`net10.0-windows`) con
   referencia a `Sistemas.Core` y `Sistemas.Core.UI`. Dentro:
   - `Models/` — los DTOs
   - `Services/` — un servicio estático por agregado
   - una carpeta por área funcional con sus `UserControl`
   - `Dashboard/` — un `IDashboardModule` por entrada del menú lateral
   - `Textos.cs` — todos los strings de esta vertical
   - `<Rubro>ModuleProvider.cs` implementando `IVerticalModuleProvider`
3. **Ejecutable** `Sistemas.<Rubro>` copiando `Program.cs` de
   `Sistemas.Repuestos` y cambiando solo el provider que se instancia.
4. **Registrar los cuatro proyectos** en `SistemasHN.slnx`.

Lo que **no** hay que hacer: tocar `DashboardModuleRegistry`, `FormDashboardBase`,
`AppBootstrapper` ni ningún `Textos.cs` de Core.

## 7. Los contratos de extensión

```csharp
// Una implementación por vertical. Es lo único que el .exe conoce de ella.
public interface IVerticalModuleProvider { void RegistrarModulos(); }

// Una implementación por entrada del menú lateral.
public interface IDashboardModule
{
    string Nombre { get; }   // rótulo en el sidebar
    string Glyph  { get; }   // UN carácter de "Segoe MDL2 Assets" — ver ADR-0011
    int    Orden  { get; }   // posición en el menú
    Control CrearVista();    // el UserControl que se monta en el panel de contenido
}
```

`DashboardModuleRegistry` es una lista estática ordenada por `Orden`. Se llena
antes del primer login y no vuelve a tocarse.

## 8. Estado de sesión

`SessionContext` es un singleton estático (`SessionContext.Current`). Es
deliberado: una app de escritorio con un usuario por proceso no necesita
inyección de dependencias para esto. Guarda `UsuarioId`, `NombreUsuario`,
`NombreCompleto`, `RolId`, `NombreRol` y la conveniencia `EsAdministrador`.

El `UsuarioId` se pasa a los SP que auditan — **no se deduce en SQL**, porque
la conexión usa autenticación integrada de Windows y todos los usuarios de la
app comparten el mismo login de SQL Server.

## 9. Configuración y archivos en disco

| Qué | Dónde | Por qué ahí |
|---|---|---|
| Connection string | `%ProgramData%\SistemasHN\appsettings.json`, con respaldo junto al `.exe` | Todas las verticales de una máquina apuntan a la misma base ([ADR-0009](decisiones/ADR-0009-connection-string-en-programdata.md)) |
| Licencia activada | `%LocalAppData%\SistemasHN\license.dat`, cifrada con DPAPI `LocalMachine` | Atada a la máquina, ilegible al copiarla a otra |
| Clave privada de firma | **Fuera del repositorio.** `Sistemas.Licencias/clave_privada.pem` está en `.gitignore` | Es el secreto que sostiene el modelo de licenciamiento |
| Logo del negocio | Configurable desde Ajustes | Marca blanca |
