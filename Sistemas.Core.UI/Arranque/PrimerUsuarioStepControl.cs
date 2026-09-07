using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Security;

namespace Sistemas.Core.UI.Arranque
{
    // Mismo contenido que FormRegistro(esPrimerUsuario: true), como paso
    // embebido en la ventana única de arranque. El caso "admin crea un
    // usuario nuevo" desde Ajustes sigue usando FormRegistro como diálogo.
    public sealed class PrimerUsuarioStepControl : UserControl
    {
        private const int PanelAncho = 720;
        private const int Margen = 48;
        private const int Ancho = PanelAncho - 2 * Margen;

        public event EventHandler<int>? UsuarioCreado;

        private readonly TextBox _txtNombreUsuario;
        private readonly TextBox _txtNombreCompleto;
        private readonly TextBox _txtPassword;
        private readonly TextBox _txtConfirmar;
        private readonly ComboBox _cboRol;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public PrimerUsuarioStepControl()
        {
            Dock = DockStyle.Fill;
            BackColor = Color.White;

            // Logo + título se centran como un solo grupo dentro del ancho
            // total del panel, en vez de quedar anclados al margen izquierdo.
            const int logoSize = 96;
            const int gap = 24;
            var lblTitulo = new Label
            {
                Text = Textos.Arranque.PrimerUsuarioTitulo,
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
                Location = new Point(headerX, 40)
            };
            lblTitulo.Location = new Point(headerX + logoSize + gap, 40 + (logoSize - lblTitulo.PreferredSize.Height) / 2);

            var lblSubtitulo = new Label
            {
                Text = Textos.Arranque.PrimerUsuarioSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                AutoSize = false,
                Size = new Size(Ancho, 24),
                Location = new Point(Margen, 156),
                TextAlign = ContentAlignment.TopCenter
            };

            int y = 212;
            var lblUsuario = new Label { Text = Textos.Dashboard.CampoNombreUsuario, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtNombreUsuario = new TextBox { Location = new Point(Margen, y + 26), Size = new Size(Ancho, 34) };

            y += 78;
            var lblNombreCompleto = new Label { Text = Textos.Dashboard.CampoNombreCompleto, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtNombreCompleto = new TextBox { Location = new Point(Margen, y + 26), Size = new Size(Ancho, 34) };

            y += 78;
            var lblPassword = new Label { Text = Textos.Dashboard.CampoPassword, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtPassword = new TextBox { Location = new Point(Margen, y + 26), Size = new Size(Ancho, 34), PasswordChar = '●' };

            y += 78;
            var lblConfirmar = new Label { Text = Textos.Dashboard.CampoConfirmarPassword, ForeColor = UiTheme.TextoOscuro, AutoSize = true, Location = new Point(Margen, y) };
            _txtConfirmar = new TextBox { Location = new Point(Margen, y + 26), Size = new Size(Ancho, 34), PasswordChar = '●' };

            y += 78;
            _cboRol = new ComboBox
            {
                Location = new Point(Margen, y),
                Size = new Size(Ancho, 34),
                DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(Sistemas.Core.Security.Models.RolDto.Nombre),
                ValueMember = nameof(Sistemas.Core.Security.Models.RolDto.Id),
                Visible = false // fijo en Administrador para el primer usuario, no se muestra
            };

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                AutoSize = false,
                Size = new Size(Ancho, 32),
                Location = new Point(Margen, y),
                TextAlign = ContentAlignment.TopCenter
            };

            y += 56;
            _btnGuardar = new Button
            {
                Text = Textos.Arranque.PrimerUsuarioTitulo,
                Size = new Size(250, 46),
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
                lblUsuario, _txtNombreUsuario,
                lblNombreCompleto, _txtNombreCompleto,
                lblPassword, _txtPassword,
                lblConfirmar, _txtConfirmar,
                _cboRol,
                _lblError, _btnGuardar
            });

            Load += PrimerUsuarioStepControl_Load;
        }

        private async void PrimerUsuarioStepControl_Load(object? sender, EventArgs e)
        {
            try
            {
                var roles = await AuthService.ListarRolesAsync();
                _cboRol.DataSource = roles.ToList();

                var admin = roles.FirstOrDefault(r => r.Nombre == "Administrador");
                if (admin != null) _cboRol.SelectedValue = admin.Id;
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            var nombreUsuario = _txtNombreUsuario.Text.Trim();
            var nombreCompleto = _txtNombreCompleto.Text.Trim();
            var password = _txtPassword.Text;

            if (nombreUsuario.Length < 3)
            {
                _lblError.Text = Textos.Dashboard.ErrorNombreUsuarioCorto;
                return;
            }
            if (nombreCompleto.Length == 0)
            {
                _lblError.Text = Textos.Dashboard.ErrorNombreCompletoRequerido;
                return;
            }
            if (password.Length < 6)
            {
                _lblError.Text = Textos.Dashboard.ErrorPasswordCorta;
                return;
            }
            if (password != _txtConfirmar.Text)
            {
                _lblError.Text = Textos.Dashboard.ErrorPasswordsNoCoinciden;
                return;
            }
            if (_cboRol.SelectedValue is not int rolId)
            {
                _lblError.Text = Textos.Arranque.ErrorNoSeDeterminoRolAdmin;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, usuarioId) = await AuthService.CrearUsuarioAsync(
                    nombreUsuario, nombreCompleto, password, rolId, usuarioCreadorId: null);

                if (exito)
                {
                    UsuarioCreado?.Invoke(this, usuarioId!.Value);
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
                _btnGuardar.Enabled = true;
            }
        }
    }
}
