using System.Windows.Forms;

namespace Sistemas.Core.UI.Dashboard
{
    // Contrato mínimo para que cualquier vertical registre sus propios
    // módulos en el Dashboard sin tener que tocar Sistemas.Core.UI.
    public interface IDashboardModule
    {
        string Nombre { get; }

        // Un solo carácter de la fuente "Segoe MDL2 Assets" (ya instalada en
        // Windows) — evita tener que producir y empaquetar imágenes .png
        // para cada icono de módulo.
        string Glyph { get; }

        int Orden { get; }

        Control CrearVista();
    }
}
