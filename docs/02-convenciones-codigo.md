# 02 — Convenciones de código (C# / WinForms)

Estas reglas describen cómo está escrito el código que ya existe. Un archivo
nuevo debe poder mezclarse con los existentes sin que se note cuál es cuál.

---

## 1. Idioma

**Todo en español**, sin excepción y sin mezclar:

- Nombres de clases, métodos, propiedades, variables y parámetros.
- Comentarios.
- Mensajes al usuario.
- Mensajes de commit.

Se conservan en inglés únicamente: las palabras clave de C#, los nombres de
tipos del framework y de paquetes de terceros, y los nombres de carpeta ya
establecidos en `Sistemas.Core` (`Inventory`, `Security`, `Licensing`, `Data`,
`Export`, `Files`, `Logging`). **No renombres esas carpetas**: el costo de
tocarlas hoy supera la inconsistencia.

Los sufijos técnicos sí van en inglés porque son convención universal de .NET:
`...Async`, `...Dto`, `...Service`.

## 2. Nombres

| Elemento | Convención | Ejemplo real |
|---|---|---|
| Clase / interfaz | `PascalCase` | `ProductService`, `IDashboardModule` |
| Método | `PascalCase`, verbo primero | `ListarAsync`, `RegistrarVentaAsync` |
| Método asíncrono | siempre sufijo `Async` | `AutenticarAsync` |
| Variable local / parámetro | `camelCase` | `tamanoPagina`, `usuarioId` |
| Campo privado | `_camelCase` | `_modulos`, `_pnlSidebar` |
| Constante | `PascalCase` | `AnchoExpandido` |
| DTO | `<Concepto>Dto` | `ProductoDto`, `CuentaPorCobrarDto` |
| Servicio | `<Concepto>Service` | `CompraService`, `ProveedorService` |
| Control WinForms | prefijo de tipo | `_pnlContenido`, `_lblApp`, `btnToggle` |

**Sin tildes ni `ñ` en identificadores**, aunque C# lo permita: `tamanoPagina`,
`AnoFiscal`. En **strings y comentarios sí van todas las tildes** — el texto lo
lee un usuario hondureño, no el compilador.

## 3. Servicios de datos

El patrón es uniforme en todo el repositorio. Un servicio es una **clase
estática** con métodos asíncronos que abren su propia conexión, llaman a un SP y
devuelven una tupla o un DTO.

```csharp
public static async Task<(bool Exito, string Mensaje, int? ProductoId)> CrearAsync(
    string codigo, string nombre, /* ... */ int? usuarioId)
{
    using var conn = ConnectionFactory.CreateConnection();
    return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? ProductoId)>(
        "Inventario.sp_CrearProducto",
        new { Codigo = codigo, Nombre = nombre, /* ... */ UsuarioId = usuarioId },
        commandType: CommandType.StoredProcedure);
}
```

Reglas que se ven ahí y hay que respetar:

- **`using var conn = ConnectionFactory.CreateConnection();`** en cada método.
  No se comparten ni se guardan conexiones: el pool de ADO.NET ya hace ese
  trabajo, y una conexión viva es un bloqueo esperando a ocurrir.
- **Siempre `commandType: CommandType.StoredProcedure`.** Nada de SQL
  interpolado. Los parámetros van en un objeto anónimo con los nombres exactos
  del SP.
- **El resultado de un SP que muta datos se mapea a una tupla con nombres**
  `(bool Exito, string Mensaje, ...)`. Es el contrato C-4 del lado de C#.
- **`UsuarioId` se pasa siempre** en toda operación auditable. Viene de
  `SessionContext.Current`.
- **Listado paginado** devuelve `QueryMultipleAsync`: primero las filas, luego
  el total. Nunca se trae la tabla completa para contar en memoria.

### La única excepción permitida a "todo por SP"

Consultas triviales de solo lectura, sin regla de negocio, pueden ir en SQL
literal dentro del servicio. Está documentado en el propio código:

```csharp
// Consulta trivial de solo lectura; no amerita un stored procedure dedicado
// (a diferencia de las operaciones que mutan datos o que aplican una regla).
var total = await conn.ExecuteScalarAsync<int>("SELECT COUNT(1) FROM Security.Usuarios");
```

Si la consulta filtra por algo que viene del usuario, **va a SP**. No hay
concatenación de strings en SQL en ninguna parte de este repositorio, y no la
va a haber.

## 4. Manejo de errores

Tres niveles, y cada uno tiene su lugar:

1. **Regla de negocio violada** → el SP devuelve `Exito = 0` con un `Mensaje`
   en español. **No es una excepción.** El servicio la devuelve tal cual y la
   pantalla la muestra con `MostrarError(...)`.
2. **Falla de infraestructura** (base caída, timeout) → excepción. Se captura
   **en la capa de UI**, no en el servicio, y se muestra con un prefijo de
   `Textos.Comun`:
   ```csharp
   catch (Exception ex)
   {
       MostrarError(Textos.Comun.NoSeConectoBdPrefijo + ex.Message);
   }
   ```
3. **Error de programación** → que reviente. No se envuelve en un `try/catch`
   vacío para "que no se caiga".

**Nunca** se muestra un mensaje crudo de SQL Server al usuario. El cliente no
tiene a quién preguntarle qué es un error 547.

## 5. Async en WinForms

- Todo lo que toca la base de datos es `async`.
- Los manejadores de eventos son `async void` — es el único lugar legítimo para
  `async void` en .NET.
- **Nunca** `.Result`, `.Wait()` ni `.GetAwaiter().GetResult()` en el hilo de UI.
  Produce un interbloqueo permanente. La razón exacta está comentada en
  `AppBootstrapper.cs` y vale la pena leerla antes de dudar.
- Si una operación puede pasar de ~300 ms, la pantalla muestra que está
  trabajando (`Cursor.Current`, botón deshabilitado, o etiqueta de estado).

## 6. Textos y colores

Regla dura R3 de `CLAUDE.md`. En detalle:

**Textos.** Tres archivos, cada uno con un alcance estricto:

| Archivo | Qué va | Qué NO va |
|---|---|---|
| `Sistemas.Core/Textos.cs` | Mensajes de la capa de negocio compartida: auth, licencia, Excel | Nada de una vertical, nada de pantallas |
| `Sistemas.Core.UI/Textos.cs` | Pantallas compartidas: arranque, dashboard, ajustes, comunes | Nada de una vertical |
| `Sistemas.Repuestos.Library/Textos.cs` | Todo lo de esa vertical | Nada compartido |

Se organizan en clases anidadas por área (`Textos.Comun`, `Textos.Auth`,
`Textos.Dashboard`) con `const string`. Los mensajes con datos variables usan
placeholders `{0}` y `string.Format`, no concatenación:

```csharp
public const string FormatoPaginacion = "Página {0} de {1}  ·  {2} fila(s)";
```

**Colores y fuentes.** Todo sale de `Sistemas.Core.UI/UiTheme.cs`. La paleta se
llama "Grafito y Vino" y sus roles están definidos ahí:
`Primario`, `PrimarioOscuro`, `SidebarFondo`, `SidebarFondoActivo`,
`SidebarTexto`, `SidebarTextoTenue`, `FondoContenido`, `TextoOscuro`,
`TextoTenue`, `Exito`, `Error`, `ErrorFondo`, `Borde`, más
`FuenteBase`, `FuenteTitulo`, `FuenteGlyph`.

Si necesitás un color que no está, **se agrega a `UiTheme` con un nombre de rol**
(qué significa), no de apariencia. `Advertencia`, no `Amarillo`.

## 7. Pantallas WinForms

- **Todo se construye por código**, no con el diseñador. No hay archivos
  `.Designer.cs` en este repositorio y no deberían aparecer: el diseñador genera
  código con colores y textos literales incrustados, que rompe R3.
- Las ventanas heredan de `FormBase`, que ya fija posición, fuente y fondo, y
  aporta `MostrarError`, `MostrarInfo` y `Confirmar`. **Usá esos helpers**, no
  `MessageBox.Show` directo.
- El contenido de un módulo es un `UserControl` que se monta en el panel del
  dashboard. No se abren ventanas nuevas para navegar; los `Form` se reservan
  para diálogos modales de captura (`FormRegistrarCompra`, `FormProveedor`).
- Las grillas se estilan con `GridStyler`, la paginación con `PaginacionControl`,
  las cantidades se formatean con `CantidadFormatter`. Antes de escribir un
  helper nuevo, revisá si ya existe en `Sistemas.Core.UI`.
- **El diseño visual y de interacción lo manda
  [`GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`](../GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md)**:
  rejilla de 4/8 px, las cinco pantallas canónicas, patrones de formulario y de
  tabla, navegación, y teclado primero. Antes de diseñar una pantalla nueva,
  preguntate a cuál de las cinco canónicas se parece y copiale la estructura.

## 8. Comentarios

Este repositorio comenta **el porqué, nunca el qué**. Es su rasgo más distintivo
y hay que sostenerlo. Comparación real del código existente:

```csharp
// ❌ Nadie escribe esto acá
// Crea la conexión
using var conn = ConnectionFactory.CreateConnection();

// ✅ Esto sí: explica una decisión que no es obvia
// No se dispone el stream: GDI+ puede decodificar la imagen de forma
// diferida y necesita el stream vivo mientras la Image esté en uso.
return Image.FromStream(stream);
```

Dónde poner un comentario:

- **Encabezado de clase:** qué rol cumple y qué frontera respeta. Ver
  `IVerticalModuleProvider.cs` o `Textos.cs`.
- **Antes de una decisión no obvia:** por qué `async void` acá, por qué este
  índice es filtrado, por qué esta cultura y no la del sistema.
- **Al lado de un valor mágico:** de dónde sale el número.
- **Referenciando un defecto conocido:** `// Defecto B-6: producto inexistente`,
  apuntando a `plan-desarrollo-base-datos.md` §3.

## 9. Cultura y formato de números

Fijada en `Program.cs` a `en-US` en `DefaultThreadCurrentCulture` (no solo en
`CurrentThread`), para que las continuaciones async y los hilos del threadpool
la hereden. Detalles y motivo en
[ADR-0008](decisiones/ADR-0008-cultura-fija-en-el-arranque.md).

Consecuencias prácticas:
- Punto decimal y coma de miles, siempre, en cualquier Windows.
- Se formatea con `"N2"` para dinero y `"N0"` para conteos. **Nunca `"C"`**: la
  moneda se antepone a mano como `L. ` porque el formato de moneda depende del
  locale y traería `$`.
