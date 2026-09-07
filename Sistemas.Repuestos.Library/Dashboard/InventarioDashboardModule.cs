using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Inventario;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class InventarioDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Inventario;
        public string Glyph => "";
        public int Orden => 10;

        public Control CrearVista() => new InventarioControl();
    }
}
