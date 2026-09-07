using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Terceros;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class ClientesDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Clientes;
        public string Glyph => "";
        public int Orden => 25;

        public Control CrearVista() => new TercerosControl(esVistaProveedores: false);
    }
}
