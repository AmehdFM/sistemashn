using System.Windows.Forms;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Terceros;

namespace Sistemas.Repuestos.Library.Dashboard
{
    public sealed class ProveedoresDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Modulos.Proveedores;
        public string Glyph => "";
        public int Orden => 20;

        public Control CrearVista() => new TercerosControl(esVistaProveedores: true);
    }
}
