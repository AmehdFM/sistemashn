using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Cuentas;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class CuentasDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.CuentasPorCobrarPagar;
        public string Glyph => "";
        public int Orden => 60;

        public Control CrearVista() => new CuentasControl();
    }
}
