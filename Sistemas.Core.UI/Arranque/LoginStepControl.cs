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
    // reducida a una atribución pequeña y discreta al pie. Todo el contenido
    // se centra como grupo dentro del panel, en vez de anclarse al margen
    // izquierdo, para que se sienta como una pantalla de inicio de sesión
    // "de verdad" y no un formulario más.
    public sealed class LoginStepControl : UserControl
    {
        private const int PanelAncho = 720;
        private const int LogoSize = 96;
        private const int CampoAncho = 440;
        private static readonly int CampoX = (PanelAncho - CampoAncho) / 2;

        public event EventHandler? SesionIniciada;

        private readonly PictureBox _picLogoCliente;
        private readonly Label _lblNombreNegocio;
        private readonly Label _lblSubtitulo;
        private readonly TextBox _txtUsuario;
        private readonly TextBox _txtPassword;
        private readonly Label _lblError;
        private readonly Button _btnEntrar;
        private readonly PictureBox _picElements;
        private readonly Label _lblAtribucion;

        public LoginStepControl()
        {
            Dock = DockStyle.Fill;
            BackColor = Color.White;

            _picLogoCliente = new PictureBox
            {
                SizeMode = PictureBoxSizeMode.Zoom,
                Size = new Size(LogoSize, LogoSize),
                Location = new Point((PanelAncho - LogoSize) / 2, 44),
                Visible = false
            };

            _lblNombreNegocio = new Label
            {
                Text = string.Empty,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.Primario,
                AutoSize = true,
                TextAlign = ContentAlignment.MiddleCenter
            };

            _lblSubtitulo = new Label
            {
                Text = Textos.Arranque.LoginSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                AutoSize = false,
                Size = new Size(600, 24),
                Location = new Point((PanelAncho - 600) / 2, 156),
                TextAlign = ContentAlignment.TopCenter
            };

            var lblUsuario = new Label { Text = Textos.Arranque.CampoUsuario, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(CampoX, 220) };
            _txtUsuario = new TextBox { Location = new Point(CampoX, 246), Size = new Size(CampoAncho, 34) };

            var lblPassword = new Label { Text = Textos.Dashboard.CampoPassword, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(CampoX, 298) };
            _txtPassword = new TextBox { Location = new Point(CampoX, 324), Size = new Size(CampoAncho, 34), PasswordChar = '●' };

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                AutoSize = false,
                Size = new Size(CampoAncho, 40),
                Location = new Point(CampoX, 376),
                TextAlign = ContentAlignment.TopCenter
            };

            _btnEntrar = new Button
            {
                Text = Textos.Arranque.BotonEntrar,
                Location = new Point(CampoX, 432),
                Size = new Size(CampoAncho, 46),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            _btnEntrar.FlatAppearance.BorderSize = 0;
            _btnEntrar.Click += BtnEntrar_Click;

            // Atribución del creador: icono + texto se centran como un solo
            // grupo, calculando su ancho combinado — igual que el
            // encabezado de las demás pantallas de arranque.
            _picElements = new PictureBox
            {
                Image = BrandingAssets.LogoCreador,
                SizeMode = PictureBoxSizeMode.Zoom,
                Size = new Size(20, 20)
            };

            _lblAtribucion = new Label
            {
                Text = Textos.Arranque.AtribucionCreador,
                ForeColor = UiTheme.TextoTenue,
                Font = new Font(UiTheme.FuenteBase.FontFamily, 9.5f),
                AutoSize = true
            };

            const int atribGap = 8;
            const int atribY = 540;
            int atribGroupWidth = _picElements.Width + atribGap + _lblAtribucion.PreferredSize.Width;
            int atribX = (PanelAncho - atribGroupWidth) / 2;
            _picElements.Location = new Point(atribX, atribY);
            _lblAtribucion.Location = new Point(atribX + _picElements.Width + atribGap, atribY + (_picElements.Height - _lblAtribucion.PreferredSize.Height) / 2);

            Controls.AddRange(new Control[]
            {
                _picLogoCliente, _lblNombreNegocio, _lblSubtitulo,
                lblUsuario, _txtUsuario, lblPassword, _txtPassword, _lblError, _btnEntrar,
                _picElements, _lblAtribucion
            });

            Load += LoginStepControl_Load;
        }

        private void CentrarNombreNegocio()
        {
            _lblNombreNegocio.Location = new Point(
                (PanelAncho - _lblNombreNegocio.PreferredSize.Width) / 2,
                44 + (LogoSize - _lblNombreNegocio.PreferredSize.Height) / 2);
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
                CentrarNombreNegocio();
            }
            catch
            {
                _lblNombreNegocio.Text = Textos.Arranque.LoginTituloGenerico;
                CentrarNombreNegocio();
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
