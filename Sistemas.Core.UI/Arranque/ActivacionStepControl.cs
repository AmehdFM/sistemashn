using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Licensing;

namespace Sistemas.Core.UI.Arranque
{
    // Mismo contenido que tenía FormActivation como Form independiente, ahora
    // como paso embebido en la ventana única de arranque (FormArranque).
    // El panel central de FormArranque tiene ancho fijo (720px, ver
    // ADR-0010) — los márgenes izquierdo/derecho del paso se logran con
    // Padding del contenedor, no con Location por control.
    public sealed class ActivacionStepControl : UserControl
    {
        private const int Margen = 48;

        public event EventHandler? Activado;

        private readonly TextBox _txtFingerprint;
        private readonly TextBox _txtClave;
        private readonly Label _lblEstado;
        private readonly Button _btnValidar;

        public ActivacionStepControl()
        {
            Dock = DockStyle.Fill;
            BackColor = Color.White;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(Margen, UiTheme.Espacio.Xxl, Margen, 0) };

            // Logo + título se centran como un solo grupo horizontal.
            var pnlEncabezado = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 96,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = false,
                Anchor = AnchorStyles.Top,
                AutoSize = true,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };
            var pic = new PictureBox
            {
                Image = BrandingAssets.LogoCreador,
                SizeMode = PictureBoxSizeMode.Zoom,
                Size = new Size(96, 96),
                Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0)
            };
            var lblTitulo = new Label
            {
                Text = Textos.Arranque.ActivacionTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Margin = new Padding(0, (96 - (int)UiTheme.FuenteTitulo.GetHeight()) / 2, 0, 0)
            };
            pnlEncabezado.Controls.AddRange(new Control[] { pic, lblTitulo });
            // Centrado horizontal del grupo dentro del panel disponible.
            pnlContenido.Resize += (s, e) => pnlEncabezado.Left = Math.Max(0, (pnlContenido.ClientSize.Width - pnlEncabezado.PreferredSize.Width) / 2);

            var lblInstrucciones = new Label
            {
                Text = Textos.Arranque.ActivacionInstrucciones,
                Dock = DockStyle.Top,
                Height = 48,
                ForeColor = UiTheme.TextoTenue,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };

            var lblFingerprintTitulo = new Label { Text = Textos.Arranque.ActivacionCodigoMaquina, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoOscuro };

            var filaFingerprint = new Panel { Dock = DockStyle.Top, Height = 34, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl) };
            var btnCopiar = new Button { Text = Textos.Arranque.BotonCopiar, Dock = DockStyle.Right, Width = 108, Height = 34, Cursor = Cursors.Hand };
            btnCopiar.Click += (s, e) =>
            {
                try { Clipboard.SetText(_txtFingerprint.Text); MostrarInfo(Textos.Arranque.CodigoCopiado); }
                catch { /* portapapeles no disponible, no es crítico */ }
            };
            _txtFingerprint = new TextBox
            {
                ReadOnly = true,
                Dock = DockStyle.Fill,
                Text = ActivationService.GetHardwareFingerprint(),
                BackColor = UiTheme.FondoContenido,
                Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0)
            };
            filaFingerprint.Controls.Add(_txtFingerprint);
            filaFingerprint.Controls.Add(btnCopiar);

            var lblClaveTitulo = new Label { Text = Textos.Arranque.ActivacionClaveTitulo, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoOscuro };

            _txtClave = new TextBox
            {
                Multiline = true,
                Dock = DockStyle.Top,
                Height = 128,
                ScrollBars = ScrollBars.Vertical,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };

            _lblEstado = new Label
            {
                Dock = DockStyle.Top,
                Height = 40,
                ForeColor = UiTheme.Error,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            var pnlBoton = new Panel { Dock = DockStyle.Top, Height = 46 };
            _btnValidar = new Button
            {
                Text = Textos.Arranque.BotonActivar,
                Size = new Size(180, 46),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Anchor = AnchorStyles.Top
            };
            _btnValidar.FlatAppearance.BorderSize = 0;
            _btnValidar.Click += BtnValidar_Click;
            pnlBoton.Resize += (s, e) => _btnValidar.Left = (pnlBoton.Width - _btnValidar.Width) / 2;
            pnlBoton.Controls.Add(_btnValidar);

            pnlContenido.Controls.Add(pnlBoton);
            pnlContenido.Controls.Add(_lblEstado);
            pnlContenido.Controls.Add(_txtClave);
            pnlContenido.Controls.Add(lblClaveTitulo);
            pnlContenido.Controls.Add(filaFingerprint);
            pnlContenido.Controls.Add(lblFingerprintTitulo);
            pnlContenido.Controls.Add(lblInstrucciones);
            pnlContenido.Controls.Add(pnlEncabezado);

            Controls.Add(pnlContenido);
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
