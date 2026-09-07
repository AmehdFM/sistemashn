using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Ventas;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class VentasDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Ventas;
        public string Glyph => "";
        public int Orden => 45;

        public Control CrearVista() => new VentasControl();
    }
}