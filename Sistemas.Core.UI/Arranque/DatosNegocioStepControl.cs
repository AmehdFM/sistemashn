using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Sistemas.Core.Configuracion;
using Sistemas.Core.Configuracion.Models;
using Sistemas.Core.Files;

namespace Sistemas.Core.UI.Arranque
{
    // Paso nuevo del arranque: datos del negocio del cliente (nombre, RTN
    // opcional, logo opcional). El RTN y los demás datos fiscales son
    // opcionales porque el sistema también se ofrece a negocios que aún
    // están formalizándose y todavía no cuentan con esa información.
    public sealed class DatosNegocioStepControl : UserControl
    {
        private const int PanelAncho = 720;
        private const int Margen = 48;
        private const int Ancho = PanelAncho - 2 * Margen;

        public event EventHandler? DatosGuardados;

        private readonly int _usuarioId;

        private readonly TextBox _txtNombreComercial;
        private readonly TextBox _txtRTN;
        private readonly TextBox _txtDireccion;
        private readonly TextBox _txtTelefono;
        private readonly TextBox _txtCorreo;
        private readonly PictureBox _picLogo;
        private readonly Label _lblEstado;
        private readonly Button _btnGuardar;

        private byte[]? _logoSeleccionado;
        private string? _logoExtension;

        public DatosNegocioStepControl(int usuarioId)
        {
            _usuarioId = usuarioId;

            Dock = DockStyle.Fill;
            BackColor = Color.White;
            AutoScroll = true;

            // Logo + título se centran como un solo grupo dentro del ancho
            // total del panel, en vez de quedar anclados al margen izquierdo.
            const int logoSize = 96;
            const int gap = 24;
            var lblTitulo = new Label
            {
                Text = Textos.Arranque.DatosNegocioTitulo,
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
                Location = new Point(headerX, 32)
            };
            lblTitulo.Location = new Point(headerX + logoSize + gap, 32 + (logoSize - lblTitulo.PreferredSize.Height) / 2);

            var lblSubtitulo = new Label
            {
                Text = Textos.Arranque.DatosNegocioSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                AutoSize = false,
                Size = new Size(Ancho, 36),
                Location = new Point(Margen, 144),
                TextAlign = ContentAlignment.TopCenter
            };

            int y = 200;
            var lblNombre = new Label { Text = Textos.Dashboard.CampoNombreComercial, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtNombreComercial = new TextBox { Location = new Point(Margen, y + 24), Size = new Size(Ancho, 32) };

            y += 68;
            var lblRTN = new Label { Text = Textos.Dashboard.CampoRtnOpcional, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtRTN = new TextBox { Location = new Point(Margen, y + 24), Size = new Size(260, 32), MaxLength = 14 };

            y += 68;
            var lblDireccion = new Label { Text = Textos.Arranque.CampoDireccionOpcional, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtDireccion = new TextBox { Location = new Point(Margen, y + 24), Size = new Size(Ancho, 32) };

            y += 68;
            var lblTelefono = new Label { Text = Textos.Arranque.CampoTelefonoOpcional, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtTelefono = new TextBox { Location = new Point(Margen, y + 24), Size = new Size(260, 32) };

            y += 68;
            var lblCorreo = new Label { Text = Textos.Arranque.CampoCorreoOpcional, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtCorreo = new TextBox { Location = new Point(Margen, y + 24), Size = new Size(Ancho, 32) };

            y += 68;
            var lblLogo = new Label { Text = Textos.Arranque.CampoLogoOpcional, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };

            _picLogo = new PictureBox
            {
                Location = new Point(Margen, y + 26),
                Size = new Size(56, 56),
                BorderStyle = BorderStyle.FixedSingle,
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = UiTheme.FondoContenido
            };

            var btnSeleccionarLogo = new Button
            {
                Text = Textos.Arranque.BotonSeleccionarImagen,
                Location = new Point(Margen + 76, y + 29),
                Size = new Size(180, 34),
                Cursor = Cursors.Hand
            };
            btnSeleccionarLogo.Click += BtnSeleccionarLogo_Click;

            y += 102;
            _lblEstado = new Label
            {
                AutoSize = false,
                Size = new Size(Ancho, 32),
                Location = new Point(Margen, y),
                TextAlign = ContentAlignment.TopCenter
            };

            y += 48;
            _btnGuardar = new Button
            {
                Text = Textos.Arranque.BotonContinuar,
                Size = new Size(200, 46),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            _btnGuardar.Location = new Point(Margen + (Ancho - _btnGuardar.Width) / 2, y);
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;

            Controls.AddRange(new Control[]
            {
                pic, lblTitulo, lblSubtitulo,
                lblNombre, _txtNombreComercial,
                lblRTN, _txtRTN,
                lblDireccion, _txtDireccion,
                lblTelefono, _txtTelefono,
                lblCorreo, _txtCorreo,
                lblLogo, _picLogo, btnSeleccionarLogo,
                _lblEstado, _btnGuardar
            });
        }

        private void BtnSeleccionarLogo_Click(object? sender, EventArgs e)
        {
            using var dialogo = new OpenFileDialog
            {
                Filter = Textos.Comun.FiltroImagenes,
                Title = Textos.Comun.TituloSeleccionarLogo
            };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                _logoSeleccionado = File.ReadAllBytes(dialogo.FileName);
                _logoExtension = Path.GetExtension(dialogo.FileName);
                // No se dispersa el MemoryStream: GDI+ puede decodificar la
                // imagen de forma diferida y necesita el stream vivo mientras
                // la Image esté en uso.
                _picLogo.Image = Image.FromStream(new MemoryStream(_logoSeleccionado));
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.Comun.NoSeCargoImagenPrefijo + ex.Message;
            }
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            var rtn = _txtRTN.Text.Trim();
            if (rtn.Length > 0 && (rtn.Length != 14 || !IsNumerico(rtn)))
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.Dashboard.ErrorRtnInvalido;
                return;
            }

            if (string.IsNullOrWhiteSpace(_txtNombreComercial.Text))
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.Dashboard.ErrorNombreComercialRequerido;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                string? logoRuta = _logoSeleccionado != null
                    ? FileStorageService.Guardar("Logos", _logoSeleccionado, _logoExtension ?? ".png")
                    : null;

                var dto = new ConfiguracionDto
                {
                    NombreComercial = _txtNombreComercial.Text.Trim(),
                    RTN = rtn.Length == 0 ? null : rtn,
                    Direccion = _txtDireccion.Text.Trim(),
                    Telefono = _txtTelefono.Text.Trim(),
                    CorreoContacto = _txtCorreo.Text.Trim(),
                    LogoRuta = logoRuta,
                    FacturacionLegalActiva = false
                };

                var (exito, mensaje) = await ConfiguracionService.GuardarAsync(dto, _usuarioId);
                if (exito)
                {
                    DatosGuardados?.Invoke(this, EventArgs.Empty);
                }
                else
                {
                    _lblEstado.ForeColor = UiTheme.Error;
                    _lblEstado.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.Comun.NoSeGuardoPrefijo + ex.Message;
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }

        private static bool IsNumerico(string s)
        {
            foreach (var c in s)
                if (!char.IsDigit(c)) return false;
            return true;
        }
    }
}
