using System.Linq;
using System.Windows.Forms;

namespace Sistemas.Core.UI.Dashboard
{
    // Pantalla "Menu": lanzador con un icono grande por cada modulo
    // disponible, como forma alternativa a la barra lateral de navegar.
    public sealed class MenuDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Dashboard.ModuloMenu;

        // Glifo "ViewAll" (grid) de la fuente Segoe MDL2 Assets.
        public string Glyph => "";

        public int Orden => 0;

        public Control CrearVista()
        {
            var otros = DashboardModuleRegistry.Modulos.Where(m => m != this).ToList();
            return new ModuleLauncherControl(otros);
        }
    }
}
