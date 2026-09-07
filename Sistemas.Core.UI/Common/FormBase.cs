using System.Windows.Forms;

namespace Sistemas.Core.UI.Common
{
    // Base visual compartida por todas las pantallas de Core. No es abstracta
    // a propósito: una Form abstracta no es diseñable en el Designer de VS.
    public class FormBase : Form
    {
        public FormBase()
        {
            StartPosition = FormStartPosition.CenterScreen;
            Font = UiTheme.FuenteBase;
            BackColor = UiTheme.FondoContenido;
        }

        protected void MostrarError(string mensaje) =>
            MessageBox.Show(this, mensaje, Textos.Comun.TituloError, MessageBoxButtons.OK, MessageBoxIcon.Error);

        protected void MostrarInfo(string mensaje) =>
            MessageBox.Show(this, mensaje, Textos.Comun.TituloInformacion, MessageBoxButtons.OK, MessageBoxIcon.Information);

        protected bool Confirmar(string mensaje) =>
            MessageBox.Show(this, mensaje, Textos.Comun.TituloConfirmar, MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes;
    }
}
