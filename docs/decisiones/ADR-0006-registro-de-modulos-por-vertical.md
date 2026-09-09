# ADR-0006 — Las verticales se enchufan por `IVerticalModuleProvider`

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

[ADR-0001](ADR-0001-core-mas-verticales-en-una-base.md) exige que Core no
conozca ninguna vertical. Pero el dashboard compartido tiene que mostrar los
módulos de la vertical activa en su menú lateral. Hace falta una forma de que la
vertical se anuncie sin que Core la nombre.

## Decisión

Dos interfaces en `Sistemas.Core.UI.Dashboard` y un registro estático:

```csharp
public interface IDashboardModule
{
    string Nombre { get; }   // rótulo del sidebar
    string Glyph  { get; }   // un carácter de Segoe MDL2 Assets — ver ADR-0011
    int    Orden  { get; }   // posición en el menú
    Control CrearVista();    // el UserControl que se monta en el contenido
}

public interface IVerticalModuleProvider { void RegistrarModulos(); }
```

- Cada entrada del menú es un `IDashboardModule`.
- Cada vertical implementa `IVerticalModuleProvider` **una sola vez**
  (`RepuestosModuleProvider`) y ahí registra todos sus módulos.
- `Program.cs` llama a `DashboardModuleRegistry.RegistrarModulosBase()` (Menú y
  Ajustes, los fijos de Core) y luego a
  `new RepuestosModuleProvider().RegistrarModulos()`.

El ejecutable conoce **una sola clase** de la vertical: su provider. Cambiar de
vertical es cambiar una línea.

El registro ocurre **una vez, antes del primer login**: no depende de la sesión,
y repetirlo dentro del bucle de sesión duplicaría las entradas del menú.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Que el `.exe` registre cada módulo concreto | Obliga a tocar `Program.cs` con cada módulo nuevo y expone las clases internas de la vertical al ejecutable |
| Descubrimiento por reflexión sobre los ensamblados | Magia difícil de depurar, arranque más lento y ningún beneficio: el exe se compila por vertical de todos modos |
| Un contenedor de inyección de dependencias | Peso y complejidad para resolver una lista de cinco elementos |

## Consecuencias

**A favor**
- Core queda cerrado a modificación y abierto a extensión, de verdad.
- `Program.cs` es idéntico entre verticales salvo una línea.
- Agregar un módulo es una clase nueva y una línea en el provider.

**En contra**
- `DashboardModuleRegistry` es estado estático global: el orden y el momento del
  registro importan y no están forzados por el compilador.
- La interfaz es deliberadamente mínima. Si un módulo necesitara permisos por
  rol o carga diferida, hay que extenderla — y eso toca Core, así que se piensa
  antes de hacerlo.
