using System.Windows.Forms;

namespace Sistemas.Core.UI.Dashboard
{
    public sealed class AjustesDashboardModule : IDashboardModule
    {
        public string Nombre => Textos.Dashboard.ModuloAjustes;

        // Glifo "Setting" (engranaje) de la fuente Segoe MDL2 Assets.
        public string Glyph => "";

        public int Orden => 99;

        public Control CrearVista() => new AjustesControl();
    }
}
