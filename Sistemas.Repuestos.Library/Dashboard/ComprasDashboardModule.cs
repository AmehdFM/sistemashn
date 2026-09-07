using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Compras;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class ComprasDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Compras;
        public string Glyph => "";
        public int Orden => 30;

        public Control CrearVista() => new ComprasControl();
    }
}
