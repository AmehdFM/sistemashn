using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Sistemas.Core.Configuracion;
using Sistemas.Core.Security;

namespace Sistemas.Core.UI.Arranque
{
    // Mismo contenido que tenía FormLogin como Form independiente, ahora como
    // paso embebido en la ventana única de arranque. A diferencia de los
    // demás pasos (que son "pantallas de configuración del sistema" y sí
    // muestran la marca de Elements System en grande), aquí se prioriza el
    // logo/nombre del NEGOCIO DEL CLIENTE — la marca del creador queda
    // reducida a una atribución pequeña y discreta al pie. El contenido se
    // centra como una tarjeta (ancho fijo, Anchor=Top) dentro del panel de
    // arranque, para que se sienta como una pantalla de inicio de sesión
    // "de verdad" y no un formulario más.
    public sealed class LoginStepControl : UserControl
    {
        private const int LogoSize = 96;
        private const int CampoAncho = 440;

        public event EventHandler? SesionIniciada;

        private readonly PictureBox _picLogoCliente;
        private readonly Label _lblNombreNegocio;
        private readonly TextBox _txtUsuario;
        private readonly TextBox _txtPassword;
        private readonly Label _lblError;
        private readonly Button _btnEntrar;

        public LoginStepControl()
        {
            Dock = DockStyle.Fill;
            BackColor = Color.White;

            var pnlTarjeta = new Panel { Width = CampoAncho, Anchor = AnchorStyles.Top, AutoSize = true, Top = UiTheme.Espacio.Xxl * 2 };
            Resize += (s, e) => pnlTarjeta.Left = Math.Max(0, (ClientSize.Width - pnlTarjeta.Width) / 2);

            var pnlLogo = new Panel { Dock = DockStyle.Top, Height = LogoSize, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg) };
            _picLogoCliente = new PictureBox
            {
                SizeMode = PictureBoxSizeMode.Zoom,
                Size = new Size(LogoSize, LogoSize),
                Anchor = AnchorStyles.Top,
                Visible = false
            };
            _lblNombreNegocio = new Label
            {
                Text = string.Empty,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.Primario,
                AutoSize = true,
                Anchor = AnchorStyles.Top
            };
            pnlLogo.Resize += (s, e) =>
            {
                _picLogoCliente.Left = (pnlLogo.Width - _picLogoCliente.Width) / 2;
                _lblNombreNegocio.Left = Math.Max(0, (pnlLogo.Width - _lblNombreNegocio.PreferredSize.Width) / 2);
                _lblNombreNegocio.Top = (LogoSize - _lblNombreNegocio.PreferredSize.Height) / 2;
            };
            pnlLogo.Controls.Add(_picLogoCliente);
            pnlLogo.Controls.Add(_lblNombreNegocio);

            var lblSubtitulo = new Label
            {
                Text = Textos.Arranque.LoginSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                Dock = DockStyle.Top,
                Height = 24,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };

            var lblUsuario = new Label { Text = Textos.Arranque.CampoUsuario, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtUsuario = new TextBox { Dock = DockStyle.Top, Height = 34, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg) };

            var lblPassword = new Label { Text = Textos.Dashboard.CampoPassword, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtPassword = new TextBox { Dock = DockStyle.Top, Height = 34, PasswordChar = '●', Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg) };

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 40,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm)
            };

            _btnEntrar = new Button
            {
                Text = Textos.Arranque.BotonEntrar,
                Dock = DockStyle.Top,
                Height = 46,
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };
            _btnEntrar.FlatAppearance.BorderSize = 0;
            _btnEntrar.Click += BtnEntrar_Click;

            pnlTarjeta.Controls.Add(_btnEntrar);
            pnlTarjeta.Controls.Add(_lblError);
            pnlTarjeta.Controls.Add(_txtPassword);
            pnlTarjeta.Controls.Add(lblPassword);
            pnlTarjeta.Controls.Add(_txtUsuario);
            pnlTarjeta.Controls.Add(lblUsuario);
            pnlTarjeta.Controls.Add(lblSubtitulo);
            pnlTarjeta.Controls.Add(pnlLogo);

            // Atribución del creador: icono + texto, centrada bajo la
            // tarjeta — discreta a propósito, no compite con la marca del
            // negocio del cliente.
            var pnlAtribucion = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 32, WrapContents = false, AutoSize = true, Anchor = AnchorStyles.Top };
            var picElements = new PictureBox { Image = BrandingAssets.LogoCreador, SizeMode = PictureBoxSizeMode.Zoom, Size = new Size(20, 20), Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            var lblAtribucion = new Label
            {
                Text = Textos.Arranque.AtribucionCreador,
                ForeColor = UiTheme.TextoTenue,
                Font = new Font(UiTheme.FuenteBase.FontFamily, 9.5f),
                AutoSize = true,
                Margin = new Padding(0, 2, 0, 0)
            };
            pnlAtribucion.Controls.AddRange(new Control[] { picElements, lblAtribucion });
            Resize += (s, e) => pnlAtribucion.Left = Math.Max(0, (ClientSize.Width - pnlAtribucion.PreferredSize.Width) / 2);

            Controls.Add(pnlAtribucion);
            Controls.Add(pnlTarjeta);

            Load += LoginStepControl_Load;
        }

        private async void LoginStepControl_Load(object? sender, EventArgs e)
        {
            try
            {
                var config = await ConfiguracionService.ObtenerAsync();
                var logo = Sistemas.Core.Files.FileStorageService.Leer(config.LogoRuta);
                if (logo is { Length: > 0 })
                {
                    // No se dispersa el MemoryStream: GDI+ puede decodificar la
                    // imagen de forma diferida y necesita el stream vivo mientras
                    // la Image esté en uso.
                    _picLogoCliente.Image = Image.FromStream(new MemoryStream(logo));
                    _picLogoCliente.Visible = true;
                    _lblNombreNegocio.Visible = false;
                    return;
                }

                _lblNombreNegocio.Text = config.Existe && !string.IsNullOrWhiteSpace(config.NombreComercial)
                    ? config.NombreComercial
                    : Textos.Arranque.LoginTituloGenerico;
            }
            catch
            {
                _lblNombreNegocio.Text = Textos.Arranque.LoginTituloGenerico;
            }
        }

        private async void BtnEntrar_Click(object? sender, EventArgs e)
        {
            var usuario = _txtUsuario.Text.Trim();
            var password = _txtPassword.Text;

            if (usuario.Length == 0 || password.Length == 0)
            {
                _lblError.Text = Textos.Arranque.ErrorIngreseUsuarioPassword;
                return;
            }

            _btnEntrar.Enabled = false;
            try
            {
                var (exito, mensaje, sesion) = await AuthService.AutenticarAsync(usuario, password);
                if (exito)
                {
                    SessionContext.Iniciar(sesion!);
                    SesionIniciada?.Invoke(this, EventArgs.Empty);
                }
                else
                {
                    _lblError.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
            finally
            {
                _btnEntrar.Enabled = true;
            }
        }
    }
}
