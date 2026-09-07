using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Ventas;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class PosDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Pos;
        public string Glyph => "";
        public int Orden => 40;

        public Control CrearVista() => new PosControl();
    }
}