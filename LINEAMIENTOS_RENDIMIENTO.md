# Lineamientos de rendimiento — SistemasHN

Este documento no es una lista genérica de buenas prácticas copiada de
internet. Es el resultado de una auditoría real de todo el proyecto (SQL +
C#), hecha para un negocio pequeño: catálogos de miles de filas, un solo
punto de venta, SQL Server Express. A esa escala, casi todo lo que "suena"
a optimización en un checklist típico (full-text search, hints de
bloqueo, colecciones especializadas para listas de decenas de elementos)
no se nota nunca y sí cuesta mantenimiento. Las reglas de abajo son las
que sí importaron cuando se auditó el código real de este repo — y el
objetivo de escribirlas es que se sigan manteniendo mientras el proyecto
crece, no que se usen como excusa para complicar código que ya funciona.

Si vas a agregar código nuevo y no estás seguro de si una técnica "extra"
vale la pena aquí: no la agregues sin medir. La sección 9 explica por qué.

## 1. Resolver en lote, nunca por fila

El error más común en código que procesa muchas filas (una importación de
Excel, un batch de cualquier tipo) es resolver una referencia externa
—una categoría por nombre, un proveedor por nombre, un producto por
código— **dentro del loop de cada fila**. Eso es un round-trip a SQL
Server por fila, y con un archivo de un par de miles de filas son un par
de miles de round-trips secuenciales.

La corrección siempre tiene la misma forma:

1. Antes del loop, saca el conjunto de valores **distintos** que vas a
   necesitar resolver (`filas.Select(f => f.Categoria).Distinct(...)`).
2. Resuélvelos en una sola consulta (`WHERE Nombre IN (...)`, o un
   Table-Valued Parameter si son muchos) y arma un `Dictionary` en
   memoria.
3. El loop por fila hace *solo* un lookup en el diccionario — cero
   round-trips adicionales.

Ejemplo real de este proyecto: `ProductService.ImportarDesdeExcelAsync`
llamaba `CategoryService.ObtenerOCrearPorNombreAsync` una vez por fila. Se
corrigió resolviendo el conjunto de nombres de categoría distintos del
archivo antes del loop. El mismo patrón se usó para el importador de
compras (`CompraService.ImportarDesdeExcelAsync`): proveedores y códigos
de producto se resuelven en lote (uno o dos round-trips totales) antes de
armar los grupos de compra, nunca por fila.

## 2. Toda regla de negocio y cálculo financiero vive en el stored procedure

C# es una capa delgada: pasa parámetros a un SP y pinta el resultado. No
reimplementa una validación ni una suma que ya hace un SP, aunque sea
"solo para mostrarla más rápido en pantalla".

Ejemplos ya en el proyecto:
- `sp_RegistrarVenta` recalcula el vuelto (`EfectivoRecibido - Total`) con
  el total que él mismo determinó — nunca confía en el número que mostró
  la calculadora de cambio en pantalla.
- `sp_CerrarCaja`/`sp_ObtenerMontoEsperadoCaja` calculan el monto esperado
  en la gaveta con la misma fórmula en un solo lugar — C# solo la muestra.

La única excepción legítima es una retroalimentación puramente visual
mientras el usuario todavía está interactuando (el vuelto que se ve en
vivo en el teclado de `FormCobroEfectivo` mientras el cajero cuenta
billetes) — y en esos casos, el valor que de verdad se graba y se usa
después (recibo, reportes) es siempre el que devolvió el SP, no el que
calculó la pantalla.

Lo que sí puede vivir en C# sin ser "lógica de negocio": agrupar en
memoria un lote que ya se trajo de la base (agrupar filas de Excel por
Proveedor+Factura antes de mandarlas al SP correspondiente), o armar un
diccionario de resolución como en la sección 1. Eso es forma de los datos,
no una regla de negocio.

## 3. DTO vs. value types — cada dato tiene su forma correcta

**No es "menos objetos siempre".** Es usar el tipo correcto para cada
propósito:

- Un DTO que Dapper materializa desde una fila de SQL Server y que
  termina en un `DataGridView.DataSource`, un `BindingList<T>` (el carrito
  del POS) o un `ComboBox.DataSource` **se queda como clase**. Es el punto
  donde una fila se vuelve algo que WinForms puede dibujar, y el
  data-binding de WinForms necesita identidad de referencia para reflejar
  cambios. Convertir esos DTOs a `struct` no ahorra nada perceptible al
  volumen de datos de esta app (decenas/cientos de filas en pantalla a la
  vez) y sí puede desincronizar la UI en silencio — un `struct` dentro de
  una lista se copia por valor; mutar la copia no actualiza lo que ve el
  usuario. Eso es un bug real, no una optimización.
- Una estructura que vive y muere dentro de un método, sin tocar ningún
  control — una clave de agrupación (`readonly record struct
  ClaveCompra(string Proveedor, string? NumeroFactura)` usada para
  agrupar filas del import de compras), un par de valores temporal para
  un lookup — sí va como `readonly record struct`. No hay razón para que
  eso viva en el heap si nunca necesita identidad ni se comparte fuera del
  método.

Regla práctica: si el objeto va a terminar bindeado a un control de
WinForms, es clase. Si es puro cálculo intermedio dentro de un método, es
value type. No hay una tercera categoría de "objetos que sobran" más allá
de la disciplina normal: no crear una lista intermedia que nadie recorre,
no envolver un objeto en otro sin necesidad.

## 4. Índices: solo donde el patrón de consulta los necesita

Un índice se agrega cuando un SP real filtra u ordena por esa columna de
forma frecuente — nunca "por si acaso". El patrón ya establecido en este
proyecto es un índice **filtrado** (`WHERE Activo = 1`, `WHERE EsCliente =
1`, etc.) con `INCLUDE` de las columnas que la consulta necesita, para
que el índice cubra la consulta completa sin un key lookup extra:

```sql
CREATE INDEX IX_Productos_Activo_Nombre
    ON Inventario.Productos(Nombre)
    INCLUDE (Codigo, PrecioUnitario, StockActual, StockMinimo, CategoriaId, TasaISV)
    WHERE Activo = 1;
```

Antes de agregar un índice nuevo: ¿qué SP lo necesita, con qué WHERE/ORDER
BY exacto? Si no puedes señalar el SP y la línea, probablemente no hace
falta todavía.

## 5. `LIKE '%x%'` está bien para búsquedas de texto libre a esta escala

Los listados con buscador (`sp_ListarProductos`, `sp_ListarClientes`,
`sp_ListarProveedores`, `sp_ListarVentas`) usan `LIKE '%' + @Busqueda +
'%'`, que por el comodín inicial no puede usar un índice b-tree normal —
hace un scan. Eso es correcto y **no hay que "arreglarlo"**: sobre una
tabla de miles de filas (no cientos de miles), un scan con un predicado
simple tarda milisegundos, imperceptible para alguien tecleando en un
buscador.

Full-text search o índices trigram son la herramienta correcta recién
cuando el catálogo crece a **cientos de miles de filas** o hay muchas
cajas golpeando el mismo listado a la vez — ninguno de los dos es el caso
de un negocio pequeño con un solo punto de venta. Meterlo antes de esa
escala es complejidad de despliegue y mantenimiento (catálogos FTS,
sincronización) que nadie va a notar que resolvió algo.

Cuando una búsqueda SÍ necesita ser rápida sobre una columna concreta —
como escanear un código de barras en el POS— la solución no es "un índice
mejor sobre el LIKE", es una consulta de match exacto separada (ver
`sp_BuscarProductoPorCodigo`, sin `LIKE`, con el índice único que ya
existe sobre esa columna). Ese es el criterio: cuando el caso de uso real
es "encontrar exactamente uno", se escribe un SP de match exacto; cuando
es "buscar texto libre en una lista paginada", `LIKE` está bien.

## 6. Transacciones cortas

El patrón que ya sigue todo SP de escritura en este proyecto
(`sp_RegistrarVenta`, `sp_RegistrarCompra`, `sp_AbrirCaja`, `sp_CerrarCaja`,
`sp_AnularVenta`) y que cualquier SP transaccional nuevo debe copiar:

1. Validar todo lo que se pueda **antes** de `BEGIN TRAN` (formato,
   existencia de referencias, reglas simples). Un error de negocio nunca
   debería costar abrir una transacción.
2. Abrir la transacción lo más tarde posible; si el SP puede ser llamado
   dentro de otra transacción ya abierta, usar `SAVE TRANSACTION` con
   nombre en vez de asumir que es la única.
3. Dentro de la transacción, re-validar con `UPDLOCK` **solo las filas
   estrictamente involucradas** (el stock de los productos de esa venta,
   no toda la tabla `Productos`; la única sesión de caja abierta, no todas
   las sesiones).
4. Commitear apenas termine la última escritura.
5. La auditoría (`Auditoria.sp_RegistrarAuditoria`) se registra **después**
   del commit — no vale la pena alargar un lock de negocio por un INSERT
   que no es crítico.

No se usan hints como `READPAST`/`ROWLOCK` en este proyecto porque no hay
contención real que resolver con un solo punto de venta — agregarlos sin
un problema de concurrencia observado es resolver algo que no existe.

## 7. Paginación siempre, con tope duro del lado del servidor

Todo listado paginado tiene un tope server-side de 500 filas por página
(`IF @TamanoPagina > 500 SET @TamanoPagina = 500`, o similar). Nunca se
trae "todo" sin límite.

Excepción explícita y aceptada: poblar un combo (proveedores, clientes)
con una sola llamada de hasta 500 filas está bien — es una query indexada,
ejecutada una sola vez al abrir el formulario, no en cada tecla. Lo que
si hay que cuidar es **avisar** cuando el total real supera ese tope
(`TotalFilas > 500`), en vez de truncar en silencio — si el negocio crece
a más de 500 proveedores activos, alguien tiene que enterarse de que el
combo no los muestra todos.

Exportar "todo" a Excel (`ExportarAExcelAsync`) también pagina en bloques
de 500 en un loop, nunca hace un `SELECT` sin límite — así nunca se carga
un dataset completo en memoria de golpe.

## 8. `async`/`await` de punta a punta

- Nunca `.Result`, `.Wait()` ni `.GetAwaiter().GetResult()` sobre código
  async — bloquea el hilo que lo llama y en WinForms puede colgar la UI.
- `async void` solo en manejadores de evento reales (`_Click`, `_Load`,
  `_KeyDown` con la firma `(object? sender, EventArgs e)`). Cualquier otro
  método async se declara `async Task` y se invoca con `await` (o `_ =
  Metodo();` si deliberadamente no se espera) — así una excepción dentro
  nunca queda sin poder capturarse.
- Cualquier operación síncrona y potencialmente lenta que corra antes del
  primer `await` de un método async bloquea igual el hilo de UI. Si hace
  I/O de archivo o parsing pesado sin API async (como ClosedXML leyendo un
  Excel), se envuelve en `await Task.Run(() => ...)`.

## 9. Qué NO hacer sin evidencia de un problema real

Estas son las técnicas que "suenan" a optimización pero que la auditoría
de este proyecto descartó explícitamente, con la razón concreta:

- **Full-text search / índices trigram** para los buscadores de texto
  libre — ver sección 5. Sin un catálogo de cientos de miles de filas, es
  complejidad de despliegue sin beneficio medible.
- **`READPAST`/`ROWLOCK` como hints por defecto** — ver sección 6. Sin
  contención real (más de una caja escribiendo al mismo tiempo sobre las
  mismas filas), no resuelven nada.
- **Diccionarios/estructuras especializadas para colecciones de decenas de
  elementos** — el carrito del POS tiene, en el peor caso, unas pocas
  decenas de líneas. Un `.FirstOrDefault()` sobre esa lista es
  instantáneo; un `Dictionary` paralelo agrega la complejidad de
  mantenerlo sincronizado con el `BindingList` por una ganancia de
  microsegundos que nadie va a medir.
- **Quitar el cursor fila-por-fila de `sp_ImportarProductosMasivo`** — es
  deliberado: el requisito de negocio es que una fila con error nunca
  tumbe el resto del lote, y SQL Server no tiene una forma set-based de
  "continúa a la siguiente fila si esta falla, y dime cuál y por qué".
  Para un Excel de un negocio pequeño (cientos de filas), el costo del
  cursor es irrelevante frente a lo que se perdería (la semántica de
  error-por-fila) si se reemplazara por algo set-based.
- **Convertir DTOs bindeados a `DataGridView`/`BindingList` en `struct`**
  — ver sección 3. Rompe el data-binding, no ahorra nada perceptible.

El mensaje de fondo: **"complejo" y "eficiente" no son sinónimos.** Código
que nadie entiende también es caro — cuesta en bugs, en tiempo para
tocarlo después, en onboarding de quien siga este proyecto. En una app de
este tamaño, el costo real de una mala lectura del código casi siempre
supera el costo de una consulta que tarda dos milisegundos más de lo
teóricamente óptimo. Antes de agregar una técnica de esta lista al
proyecto, hace falta poder señalar el problema real que resuelve — no
"podría ser más rápido en teoría".
