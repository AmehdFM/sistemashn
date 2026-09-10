using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Caja;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class CajaDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Caja;
        public string Glyph => "";

        // Entre POS (40) y Ventas (45): la caja se abre/cierra alrededor del
        // turno de ventas del día.
        public int Orden => 42;

        public Control CrearVista() => new CajaControl();
    }
}
