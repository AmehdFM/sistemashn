using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.UI.Common;

namespace Sistemas.Core.UI.Dashboard
{
    // Diálogo emergente para configurar el rango de CAI, abierto desde la
    // pestaña "Facturación" de Ajustes cuando el negocio activa el
    // interruptor de facturación legal.
    public sealed class FormFacturacionCai : FormBase
    {
        public FormFacturacionCai()
        {
            Text = Textos.Dashboard.TituloConfigurarCai;
            ClientSize = new Size(660, 480);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(600, 420);

            Controls.Add(new FacturacionCaiControl());
        }
    }
}
