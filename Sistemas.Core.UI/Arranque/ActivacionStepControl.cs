using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Licensing;

namespace Sistemas.Core.UI.Arranque
{
    // Mismo contenido que tenía FormActivation como Form independiente, ahora
    // como paso embebido en la ventana única de arranque (FormArranque).
    public sealed class ActivacionStepControl : UserControl
    {
        private const int PanelAncho = 720;
        private const int Margen = 48;
        private const int Ancho = PanelAncho - 2 * Margen;

        public event EventHandler? Activado;

        private readonly TextBox _txtFingerprint;
        private readonly TextBox _txtClave;
        private readonly Label _lblEstado;
        private readonly Button _btnValidar;

        public ActivacionStepControl()
        {
            Dock = DockStyle.Fill;
            BackColor = Color.White;

            // Logo + título se centran como un solo grupo dentro del ancho
            // total del panel, en vez de quedar anclados al margen izquierdo.
            const int logoSize = 96;
            const int gap = 24;
            var lblTitulo = new Label
            {
                Text = Textos.Arranque.ActivacionTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true
            };
            int headerX = (PanelAncho - (logoSize + gap + lblTitulo.PreferredSize.Width)) / 2;

            var pic = new PictureBox
            {
                Image = BrandingAssets.LogoCreador,
                SizeMode = PictureBoxSizeMode.Zoom,
                Size = new Size(logoSize, logoSize),
                Location = new Point(headerX, 44)
            };
            lblTitulo.Location = new Point(headerX + logoSize + gap, 44 + (logoSize - lblTitulo.PreferredSize.Height) / 2);

            var lblInstrucciones = new Label
            {
                Text = Textos.Arranque.ActivacionInstrucciones,
                AutoSize = false,
                Size = new Size(Ancho, 48),
                Location = new Point(Margen, 184),
                ForeColor = UiTheme.TextoTenue,
                TextAlign = ContentAlignment.TopCenter
            };

            var lblFingerprintTitulo = new Label
            {
                Text = Textos.Arranque.ActivacionCodigoMaquina,
                AutoSize = true,
                ForeColor = UiTheme.TextoOscuro,
                Location = new Point(Margen, 258)
            };

            _txtFingerprint = new TextBox
            {
                ReadOnly = true,
                Location = new Point(Margen, 284),
                Size = new Size(Ancho - 116, 34),
                Text = ActivationService.GetHardwareFingerprint(),
                BackColor = UiTheme.FondoContenido
            };

            var btnCopiar = new Button
            {
                Text = Textos.Arranque.BotonCopiar,
                Location = new Point(Margen + Ancho - 108, 284),
                Size = new Size(108, 34),
                Cursor = Cursors.Hand
            };
            btnCopiar.Click += (s, e) =>
            {
                try { Clipboard.SetText(_txtFingerprint.Text); MostrarInfo(Textos.Arranque.CodigoCopiado); }
                catch { /* portapapeles no disponible, no es crítico */ }
            };

            var lblClaveTitulo = new Label
            {
                Text = Textos.Arranque.ActivacionClaveTitulo,
                AutoSize = true,
                ForeColor = UiTheme.TextoOscuro,
                Location = new Point(Margen, 344)
            };

            _txtClave = new TextBox
            {
                Multiline = true,
                Location = new Point(Margen, 370),
                Size = new Size(Ancho, 128),
                ScrollBars = ScrollBars.Vertical
            };

            _lblEstado = new Label
            {
                AutoSize = false,
                Size = new Size(Ancho, 40),
                Location = new Point(Margen, 510),
                ForeColor = UiTheme.Error,
                TextAlign = ContentAlignment.TopCenter
            };

            _btnValidar = new Button
            {
                Text = Textos.Arranque.BotonActivar,
                Size = new Size(180, 46),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            _btnValidar.Location = new Point(Margen + (Ancho - _btnValidar.Width) / 2, 566);
            _btnValidar.FlatAppearance.BorderSize = 0;
            _btnValidar.Click += BtnValidar_Click;

            Controls.AddRange(new Control[]
            {
                pic, lblTitulo, lblInstrucciones, lblFingerprintTitulo, _txtFingerprint, btnCopiar,
                lblClaveTitulo, _txtClave, _lblEstado, _btnValidar
            });
        }

        private void BtnValidar_Click(object? sender, EventArgs e)
        {
            if (ActivationService.ValidateActivationKey(_txtClave.Text.Trim(), out var mensaje))
            {
                Activado?.Invoke(this, EventArgs.Empty);
            }
            else
            {
                _lblEstado.Text = mensaje;
            }
        }

        private void MostrarInfo(string mensaje) =>
            MessageBox.Show(FindForm(), mensaje, Textos.Comun.TituloInformacion, MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}
