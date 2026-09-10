using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.UI.Common;

namespace Sistemas.Core.UI.Arranque
{
    // Ventana única de arranque: reemplaza el patrón anterior de abrir y
    // cerrar una Form por paso (Activación → Registro → Login), que se
    // sentía entrecortado. Un panel central de tamaño fijo, centrado dentro
    // de la ventana maximizada, se limpia y se rellena con cada paso — mismo
    // mecanismo que ya usa FormDashboardBase para navegar entre módulos.
    public sealed class FormArranque : FormBase
    {
        private readonly Panel _pnlCentral;

        public FormArranque()
        {
            Text = Textos.Arranque.TituloVentana;
            Icon = BrandingAssets.IconoApp;
            WindowState = FormWindowState.Maximized;
            BackColor = Color.White;

            // Sin borde ni color distinto al del fondo: el panel solo sirve
            // para centrar el contenido, no para "recortar" una tarjeta
            // visible sobre el fondo — toda la ventana es una única
            // superficie blanca continua.
            _pnlCentral = new Panel
            {
                Size = new Size(720, 780),
                BackColor = Color.White,
                BorderStyle = BorderStyle.None
            };

            Controls.Add(_pnlCentral);

            Resize += (s, e) => CentrarPanel();
            Load += (s, e) => CentrarPanel();
        }

        private void CentrarPanel()
        {
            _pnlCentral.Location = new Point(
                Math.Max(0, (ClientSize.Width - _pnlCentral.Width) / 2),
                Math.Max(0, (ClientSize.Height - _pnlCentral.Height) / 2));
        }

        public void MostrarPaso(Control paso)
        {
            foreach (Control saliente in _pnlCentral.Controls.Cast<Control>().ToArray())
                saliente.Dispose();
            _pnlCentral.Controls.Clear();

            paso.Dock = DockStyle.Fill;
            _pnlCentral.Controls.Add(paso);
        }
    }
}
