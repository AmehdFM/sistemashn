# Mejora integral UI/UX de SistemasHN — Plan de implementación

> **Para agentes ejecutores:** SUB-HABILIDAD OBLIGATORIA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`) para registrar avance.

**Objetivo:** Convertir la base visual actual en un sistema de diseño obligatorio, reorganizar la navegación por flujo de trabajo y migrar todas las pantallas sin cambiar la arquitectura Core + verticales.

**Arquitectura:** `Sistemas.Core.UI` seguirá siendo dueño de tokens, componentes y shell; cada vertical aportará metadatos y compondrá esos controles sin que Core conozca el dominio. La migración será incremental: primero fundamentos, después shell y patrones, finalmente familias de pantallas de menor a mayor riesgo.

**Stack:** .NET 10, WinForms, C#, Segoe UI, Segoe MDL2 Assets, SQL Server Express y herramientas incluidas en el repositorio; sin paquetes nuevos.

**Especificación:** `docs/ui-ux/01-especificacion-sistema-diseno.md` y `docs/ui-ux/02-arquitectura-navegacion.md`.

## Restricciones globales

- La línea base es el árbol de trabajo actual, incluidos sus cambios sin commit.
- No usar un worktree basado únicamente en `HEAD`: omitiría cambios que forman parte de la línea base. Trabajar en el directorio actual o guardar primero la línea base en una rama autorizada.
- No descartar, revertir ni reformatear cambios ajenos a la tarea activa.
- Mantener WinForms, `FormDashboardBase`, `IDashboardModule`, Dapper y la separación Core + verticales.
- Core nunca puede referenciar `Sistemas.Repuestos.*`.
- Ningún texto visible fuera del `Textos.cs` de su capa.
- Ningún color o fuente de interfaz fuera de `UiTheme.cs`; `ReciboPrinter` conserva su excepción de impresión.
- No agregar paquetes NuGet, servicios, fuentes ni iconos externos.
- Mantener los 220 px expandido y 56 px colapsado de ADR-0010.
- Mantener funcionamiento offline y evitar trabajo costoso en el hilo de UI.
- Cada tarea termina con `dotnet build SistemasHN.slnx` y la comprobación manual indicada.
- Commits en español, pequeños y dedicados a una tarea aceptada.
- No mezclar cambios de base de datos o reglas de negocio con el rediseño.

## Foco de revisión

1. **Línea base no confirmada:** comprobar que los cambios UI existentes siguen presentes antes de editar; nunca reconstruir desde `HEAD` silenciosamente.
2. **DPI 125/150 %:** ninguna altura fija puede cortar texto, botones o mensajes; probar 1366×768 y 1920×1080.
3. **Doble acción primaria:** cada modo visible debe tener una sola acción de acento.
4. **Carga o error con datos anteriores:** aclarar si los datos visibles están desactualizados y evitar acciones sobre selección obsoleta.
5. **Teclado y doble envío:** Enter, Escape, Tab y atajos mantienen foco lógico; una acción async en curso impide clic o tecla repetida.

---

## Mapa de archivos

### Compartidos que se modificarán

- `Sistemas.Core.UI/UiTheme.cs`: tokens y métricas.
- `Sistemas.Core.UI/Textos.cs`: textos genéricos y accesibilidad.
- `Sistemas.Core.UI/Common/FormBase.cs`: diálogos y DPI.
- `Sistemas.Core.UI/Controles/Botones.cs`: variantes y estado ocupado.
- `Sistemas.Core.UI/Controles/FormularioLayout.cs`: anchos, errores y secciones.
- `Sistemas.Core.UI/Controles/EstadoListaControl.cs`: estados.
- `Sistemas.Core.UI/GridStyler.cs`: columnas y formatos.
- `Sistemas.Core.UI/PaginacionControl.cs`: rango, total y teclado.
- `Sistemas.Core.UI/Dashboard/*.cs`: metadatos, orden y shell.

### Compartidos que se crearán

- `Sistemas.Core.UI/Controles/BotonAyudaContextual.cs`
- `Sistemas.Core.UI/Controles/EncabezadoPagina.cs`
- `Sistemas.Core.UI/Controles/EncabezadoSeccion.cs`
- `Sistemas.Core.UI/Controles/BannerEstado.cs`
- `Sistemas.Core.UI/Controles/BarraHerramientasLista.cs`
- `Sistemas.Core.UI/Controles/BarraFiltros.cs`
- `scripts/validar-ui.ps1`

No crear una superclase que conozca todos los casos. Preferir controles pequeños y composición.

---

### Tarea 1: Congelar la línea base y automatizar reglas estáticas

**Archivos:**
- Crear: `scripts/validar-ui.ps1`
- Modificar: `GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md:114`
- Modificar: `docs/08-flujo-de-trabajo-con-ia.md`

**Interfaces:**
- Consume: R2–R4 de `CLAUDE.md` y excepción de `ReciboPrinter`.
- Produce: `powershell -ExecutionPolicy Bypass -File scripts/validar-ui.ps1`.

- [ ] **Paso 1: registrar la línea base**

Ejecutar `git status --short`, `git diff --stat` y `dotnet build SistemasHN.slnx`. Conservar la salida en la entrega. Si el build falla, registrar errores preexistentes.

- [ ] **Paso 2: resolver contradicción del sidebar**

Cambiar en la guía `240/48` por `220/56` y citar ADR-0010. No alterar otras reglas.

- [ ] **Paso 3: crear el validador**

Revisar solo fuentes, excluyendo `bin/obj`, y fallar por:

```text
new Font( fuera de UiTheme.cs y ReciboPrinter.cs
Color.FromArgb o ColorTranslator.FromHtml fuera de UiTheme.cs
Color.White/Black/Gray/Red/Green/Blue fuera de UiTheme.cs
ToolTip con literal visible fuera de Textos.cs
```

Imprimir `archivo:línea:regla`; mantener excepciones explícitas y comentadas.

- [ ] **Paso 4: ejecutar y registrar deuda inicial**

El script puede fallar en esta tarea, pero cada hallazgo debe ser real y quedar enumerado.

- [ ] **Paso 5: agregar el comando a `docs/08-flujo-de-trabajo-con-ia.md`**

Incluirlo en criterios de terminado de pantallas.

- [ ] **Paso 6: verificar**

Ejecutar `git diff --check` y build.

- [ ] **Paso 7: commit**

```powershell
git add GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md docs/08-flujo-de-trabajo-con-ia.md scripts/validar-ui.ps1
git commit -m "Establece controles automaticos del sistema visual"
```

---

### Tarea 2: Completar tokens, métricas y botones

**Archivos:**
- Modificar: `Sistemas.Core.UI/UiTheme.cs`
- Modificar: `Sistemas.Core.UI/Controles/Botones.cs`
- Modificar: `Sistemas.Core.UI/Textos.cs`
- Migrar estilos locales en shell, lanzador, cobro, compras y POS.

**Interfaces:**
- Produce: `UiTheme.AnchosCampo`, métricas completas y variantes primaria, secundaria, terciaria, destructiva e icono.

- [ ] **Paso 1: agregar roles faltantes**

Agregar fondo de control, control deshabilitado, texto deshabilitado, hover neutro, borde fuerte y foco. Validar 4.5:1 para texto y 3:1 para bordes/iconos funcionales.

- [ ] **Paso 2: agregar anchos semánticos**

```csharp
public static class AnchosCampo
{
    public const int MuyCorto = 72;
    public const int Corto = 120;
    public const int Medio = 220;
    public const int Largo = 320;
    public const int ExpandibleMinimo = 320;
}
```

Agregar objetivo de icono 32, sidebar 220/56, ítem 44 y multilinea 96; conservar tokens actuales.

- [ ] **Paso 3: centralizar fuentes restantes**

Agregar tokens para glifo de lanzador, total secundario y botón de colapso. Sustituir `new Font` locales, salvo impresión.

- [ ] **Paso 4: completar variantes**

`CrearDestructivo` usa Error; `CrearTerciario` no usa acento. Cambiar icono a:

```csharp
public static Button CrearIcono(string glyph, string nombreAccesible, string tooltip)
```

No dejar una sobrecarga que cree iconos sin nombre.

- [ ] **Paso 5: agregar estado ocupado**

```csharp
public static void MarcarOcupado(Button boton, bool ocupado, string textoOcupado)
```

Conservar texto/estado previos, impedir doble envío y restaurar en `finally`.

- [ ] **Paso 6: migrar consumidores sin cambiar layout**

Reemplazar solo estilos locales identificados por el script.

- [ ] **Paso 7: verificar**

Script, `git diff --check` y build; cero estilos sueltos salvo excepciones.

- [ ] **Paso 8: commit**

`git commit -m "Completa tokens y variantes visuales compartidas"`.

---

### Tarea 3: Crear componentes estructurales

**Archivos:** crear los seis controles compartidos descritos en el mapa; modificar `FormularioLayout.cs` y `Textos.cs`.

**Interfaces:**
- `BotonAyudaContextual(string nombreCampo, string ayudaCorta, string? ayudaExtendida = null)`.
- `EncabezadoPagina`: Titulo, Descripcion, MostrarVolver, VolverSolicitado y acciones.
- `BannerEstado.Mostrar(TipoBanner tipo, string mensaje, string? textoAccion)`.
- Toolbars/filtros aceptan controles genéricos.

- [ ] **Paso 1:** Implementar ayuda con glifo MDL2, 32×32, tooltip, `AccessibleName`, `AccessibleDescription` y evento extendido.
- [ ] **Paso 2:** Implementar encabezados con AutoSize y tokens.
- [ ] **Paso 3:** Implementar banner Información/Éxito/Advertencia/Error con acción opcional.
- [ ] **Paso 4:** Implementar toolbar separando principal, selección y utilidades.
- [ ] **Paso 5:** Implementar filtros con búsqueda expandible, filtros y Limpiar.
- [ ] **Paso 6:** Ampliar FormularioLayout con ancho semántico, error y sección, manteniendo firmas existentes.
- [ ] **Paso 7:** Componer una prueba temporal, revisar 100/125/150 % y retirarla antes del commit.
- [ ] **Paso 8:** Build, revisión de foco y commit `"Agrega componentes estructurales de interfaz"`.

---

### Tarea 4: Estandarizar tablas, estados y paginación

**Archivos:** `GridStyler.cs`, `PaginacionControl.cs`, `EstadoListaControl.cs`, `Textos.cs`.

**Interfaces:** conservar `Aplicar` y `ComoColumnaNumerica`; agregar fecha, estado, texto y columna flexible.

- [ ] **Paso 1:** Desactivar wrap, mantener filas uniformes, tooltip de truncado, foco y selección accesible.
- [ ] **Paso 2:** Crear `ComoColumnaFecha`, `ComoColumnaEstado`, `ComoColumnaTexto` y `MarcarComoFlexible`.
- [ ] **Paso 3:** Hacer que EstadoLista limpie acción previa, exponga estado actual y anuncie cambios.
- [ ] **Paso 4:** Mostrar `Página X de Y` y `Mostrando A–B de N`; conservar sobrecarga actual.
- [ ] **Paso 5:** Probar 0, 1, 25, 26 y 10 000 filas lógicas; primera/intermedia/última página.
- [ ] **Paso 6:** Build y commit `"Unifica tablas estados y paginacion"`.

---

### Tarea 5: Reorganizar navegación y shell

**Archivos:** todos los archivos de `Sistemas.Core.UI/Dashboard/`, los siete módulos de `Sistemas.Repuestos.Library/Dashboard/` y ambos `Textos.cs`.

**Interfaces:**

```csharp
public enum GrupoNavegacion { Operacion, Gestion, Utilidades }

public interface IDashboardModule
{
    string Nombre { get; }
    string Glyph { get; }
    GrupoNavegacion Grupo { get; }
    int Orden { get; }
    bool MostrarEnInicio { get; }
    Control CrearVista();
}
```

- [ ] **Paso 1:** Agregar metadatos genéricos y actualizar todos los módulos en el mismo cambio compilable.
- [ ] **Paso 2:** Asignar Operación: Inicio 0, POS 10, Caja 20, Ventas 30; Gestión: Inventario 10, Compras 20, Clientes 30, Proveedores 40; Utilidades: Ajustes 100.
- [ ] **Paso 3:** Ordenar por grupo/orden y rechazar registros duplicados por tipo.
- [ ] **Paso 4:** Construir sidebar con header/pie fijos y scroll solo en módulos.
- [ ] **Paso 5:** En colapsado, tooltip, foco, nombre accesible y acceso alternativo a sesión.
- [ ] **Paso 6:** Marcar activo mediante indicador adicional al color.
- [ ] **Paso 7:** Convertir Menú en Inicio transitorio; priorizar POS, compra, inventario y terceros sin métricas ficticias.
- [ ] **Paso 8:** Navegar 30 veces y cerrar/iniciar sesión; no duplicar módulos ni handlers.
- [ ] **Paso 9:** Probar 1366×768 expandido/colapsado.
- [ ] **Paso 10:** Build y commit `"Ordena la navegacion por flujo operativo"`.

---

### Tarea 6: Migrar Lista/Consulta

**Archivos:** `TercerosControl.cs`, `ComprasControl.cs`, `VentasControl.cs`, `CajaControl.cs`, ambos paneles de cuentas, `FormUnidadesMedida.cs` y textos.

- [ ] **Paso 1:** Migrar Terceros como referencia: encabezado, Nuevo primario, Editar condicionado, búsqueda, limpiar, estado y paginación.
- [ ] **Paso 2:** Validar modos Clientes y Proveedores sin duplicar layout.
- [ ] **Paso 3:** Migrar Compras y Ventas; importar/exportar/anular son secundarias.
- [ ] **Paso 4:** Migrar Caja y cuentas; mostrar solo una primaria según estado.
- [ ] **Paso 5:** Migrar Unidades como catálogo simple: alta superior y tabla inferior.
- [ ] **Paso 6:** Normalizar columnas; una flexible por tabla, números a la derecha, sin autosize por contenido.
- [ ] **Paso 7:** Probar datos, cargando, vacío inicial, vacío filtrado y error; bloquear selección obsoleta.
- [ ] **Paso 8:** Verificar Ctrl+F, F5, Enter/doble clic y Tab.
- [ ] **Paso 9:** Crear commits separados para Terceros, operaciones y cuentas/catálogos.

---

### Tarea 7: Migrar diálogos y formularios breves

**Archivos:** formularios Abrir/Cerrar caja, Registrar pago, Categoría rápida, Tercero, Perfil, `TerceroCamposControl` y `FormRegistro`.

- [ ] **Paso 1:** Fijar plantilla: título, descripción opcional, formulario, error local y pie Guardar/Cancelar.
- [ ] **Paso 2:** Configurar `AcceptButton`, `CancelButton`, foco inicial y estado ocupado.
- [ ] **Paso 3:** Migrar caja/pago con ancho monetario común y alineación derecha.
- [ ] **Paso 4:** Migrar Categoría rápida y devolver selección/foco al llamador.
- [ ] **Paso 5:** Migrar `TerceroCamposControl` una vez para que ambos Forms hereden.
- [ ] **Paso 6:** Migrar registro de usuario sin revelar detalles de seguridad.
- [ ] **Paso 7:** Probar 100/125/150 %, textos largos y doble Enter.
- [ ] **Paso 8:** Build, script y commit `"Unifica dialogos y formularios breves"`.

---

### Tarea 8: Migrar Arranque y Ajustes

**Archivos:** `FormArranque.cs`, cuatro pasos, `AjustesControl.cs`, `FacturacionCaiControl.cs`, `FormFacturacionCai.cs` y textos.

- [ ] **Paso 1:** Definir anatomía de paso: progreso, título, explicación, contenido, error y primaria.
- [ ] **Paso 2:** Migrar Activación, Primer usuario, Negocio y Login conservando lógica y orden.
- [ ] **Paso 3:** Reorganizar Ajustes en Negocio, Identidad, Facturación, Catálogos y Usuarios.
- [ ] **Paso 4:** Mantener Guardar cambios como única primaria general.
- [ ] **Paso 5:** Migrar CAI distinguiendo advertencia y error.
- [ ] **Paso 6:** Probar base nueva y configurada: activación→usuario→negocio→login y login directo.
- [ ] **Paso 7:** Build y commit `"Estandariza arranque y configuracion"`.

---

### Tarea 9: Migrar Inventario maestro-detalle

**Archivos:** `InventarioControl.cs`, `ProductCard.cs`, `ProductDetailControl.cs`, textos.

- [ ] **Paso 1:** Aplicar encabezado, filtros y paginación a lista/tarjetas.
- [ ] **Paso 2:** Probar tarjetas en uno, dos y tres anchos sin huecos ni cortes.
- [ ] **Paso 3:** Extraer secciones Información, Repuesto, Vehículos, Equivalencias y Precios solo para reducir responsabilidades.
- [ ] **Paso 4:** Centralizar modos Lectura/Edición/Nuevo en un solo método.
- [ ] **Paso 5:** En lectura mostrar valores; en edición controles. Una primaria por modo.
- [ ] **Paso 6:** Reemplazar tres botones `?` por `BotonAyudaContextual` y mover textos.
- [ ] **Paso 7:** Normalizar grillas internas y acciones Agregar.
- [ ] **Paso 8:** Probar buscar→abrir→editar/cancelar/guardar→volver, conservando filtro/selección.
- [ ] **Paso 9:** Abrir/cerrar 30 veces para detectar handlers duplicados.
- [ ] **Paso 10:** Commit separado de lista/tarjetas y detalle/secciones.

---

### Tarea 10: Migrar POS y cobro

**Archivos:** `PosControl.cs`, `FormCobroEfectivo.cs`, textos.

- [ ] **Paso 1:** Registrar recorrido de teclado actual como caracterización.
- [ ] **Paso 2:** Estructurar búsqueda/producto, carrito, datos de venta y resumen fijo.
- [ ] **Paso 3:** Mantener Total y Cobrar visibles a 1366×768.
- [ ] **Paso 4:** Implementar Ctrl+F buscar, Enter agregar, Delete quitar protegido, F12 cobrar y Escape modal; mostrar `Cobrar (F12)`.
- [ ] **Paso 5:** Si caja está cerrada, Abrir caja es la única primaria; abierta, Cobrar.
- [ ] **Paso 6:** Reemplazar `+` de cliente por acción accesible y restaurar foco.
- [ ] **Paso 7:** Migrar cobro: total, recibido, vuelto, error específico y envío único.
- [ ] **Paso 8:** Probar contado, crédito, ISV mixto, stock insuficiente, cliente nuevo, efectivo exacto y vuelto.
- [ ] **Paso 9:** Confirmar que venta simple no requiere más pasos ni mouse.
- [ ] **Paso 10:** Build y commit `"Optimiza la experiencia de venta y cobro"`.

---

### Tarea 11: Migrar compras, paquetes e importaciones

**Archivos:** `FormRegistrarCompra.cs`, ambas importaciones, `FormArmarPaquete.cs`, textos.

- [ ] **Paso 1:** En compra separar proveedor/documento, búsqueda/agregado, líneas, crédito y total.
- [ ] **Paso 2:** Registrar compra es primaria; Agregar línea es secundaria.
- [ ] **Paso 3:** Unificar importaciones: Plantilla→Archivo→Previsualizar→Importar→Resumen.
- [ ] **Paso 4:** Truncar ruta larga con tooltip; estados por fila usan texto además de color.
- [ ] **Paso 5:** En paquete separar búsqueda/agregado de componentes/total; Guardar es primaria.
- [ ] **Paso 6:** Probar archivo ausente, inválido, mixto y válido; paquete vacío, duplicado y cantidad inválida.
- [ ] **Paso 7:** Build y commits separados para compra, importaciones y paquetes.

---

### Tarea 12: Cerrar accesibilidad y DPI

**Archivos:** `FormBase.cs`, `Sistemas.Repuestos/Program.cs` solo con evidencia, pantallas con hallazgos y validador.

- [ ] **Paso 1:** Verificar modo DPI real en 100/125/150 % y entre monitores. `ApplicationConfiguration.Initialize()` puede configurarlo; no duplicar sin evidencia.
- [ ] **Paso 2:** Si falta PerMonitorV2, usar la configuración soportada por el proyecto .NET 10 sin mezclar mecanismos.
- [ ] **Paso 3:** Revisar `AccessibleName`, `AccessibleDescription`, `TabIndex`, `AcceptButton`, `CancelButton` y atajos.
- [ ] **Paso 4:** Probar nombres, productos y mensajes largos; sustituir alturas problemáticas por AutoSize/MaximumSize.
- [ ] **Paso 5:** Ejecutar completa `05-checklist-qa-visual.md`.
- [ ] **Paso 6:** Ejecutar script, build y `git diff --check`.
- [ ] **Paso 7:** Commit `"Cierra accesibilidad y escalado de la interfaz"`.

---

### Tarea 13: Cierre documental e integral

**Archivos:** matriz, checklist, `docs/05-estado-y-roadmap.md` y README de UI/UX.

- [ ] **Paso 1:** Marcar pantalla con evidencia; no declarar Conforme por inspección.
- [ ] **Paso 2:** Recorrer arranque, login, venta, compra, inventario, tercero, caja, cuentas, importación y ajustes, incluidos errores de `docs/07-estrategia-de-pruebas.md`.
- [ ] **Paso 3:** Buscar referencias Core→Repuestos, dependencias, textos y estilos sueltos.
- [ ] **Paso 4:** Actualizar roadmap con implementado y deuda explícita.
- [ ] **Paso 5:** Solicitar revisión independiente de rama completa: negocio, consistencia, DPI, memoria y teclado.
- [ ] **Paso 6:** Corregir hallazgos, ejecutar build/script/diff-check.
- [ ] **Paso 7:** Commit `"Documenta la conformidad UI UX del sistema"`.

---

## Dependencias

```text
T1 Línea base
 └─ T2 Tokens
     ├─ T3 Componentes
     │   ├─ T5 Navegación
     │   ├─ T7 Diálogos
     │   └─ T8 Arranque/Ajustes
     └─ T4 Tablas
         └─ T6 Listas
             ├─ T9 Inventario
             ├─ T10 POS
             └─ T11 Compras/importaciones
                 └─ T12 Accesibilidad/DPI
                     └─ T13 Cierre
```

T3 y T4 solo pueden hacerse en paralelo si se acuerdan firmas antes. T9, T10 y T11 pueden revisarse por separado, pero no editar simultáneamente `Textos.cs` en el mismo directorio.

## Estrategia de commits

- Un commit por componente o familia verificable.
- Nunca combinar shell, POS y formularios en un commit.
- Compilar antes de cada commit.
- Mantener commits separados hasta la revisión integral para localizar regresiones.

