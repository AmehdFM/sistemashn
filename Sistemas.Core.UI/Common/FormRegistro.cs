using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Security;

namespace Sistemas.Core.UI.Common
{
    // Diálogo emergente para el caso "un administrador crea un usuario
    // nuevo" desde Ajustes. El caso "primer usuario del sistema" ya no usa
    // esta Form: vive como PrimerUsuarioStepControl dentro de la ventana
    // única de arranque (Sistemas.Core.UI.Arranque).
    public class FormRegistro : FormBase
    {
        private readonly TextBox _txtNombreUsuario;
        private readonly TextBox _txtNombreCompleto;
        private readonly TextBox _txtPassword;
        private readonly TextBox _txtConfirmar;
        private readonly ComboBox _cboRol;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FormRegistro()
        {
            Text = Textos.Dashboard.RegistroTituloVentana;
            ClientSize = new Size(420, 420);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;

            var lblTitulo = new Label
            {
                Text = Textos.Dashboard.RegistroTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Location = new Point(24, 20)
            };

            var lblSubtitulo = new Label
            {
                Text = Textos.Dashboard.RegistroSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                AutoSize = false,
                Size = new Size(372, 36),
                Location = new Point(24, 52)
            };

            int y = 100;
            var lblUsuario = new Label { Text = Textos.Dashboard.CampoNombreUsuario, AutoSize = true, Location = new Point(24, y) };
            _txtNombreUsuario = new TextBox { Location = new Point(24, y + 20), Size = new Size(372, 26) };

            y += 56;
            var lblNombreCompleto = new Label { Text = Textos.Dashboard.CampoNombreCompleto, AutoSize = true, Location = new Point(24, y) };
            _txtNombreCompleto = new TextBox { Location = new Point(24, y + 20), Size = new Size(372, 26) };

            y += 56;
            var lblPassword = new Label { Text = Textos.Dashboard.CampoPassword, AutoSize = true, Location = new Point(24, y) };
            _txtPassword = new TextBox { Location = new Point(24, y + 20), Size = new Size(372, 26), PasswordChar = '●' };

            y += 56;
            var lblConfirmar = new Label { Text = Textos.Dashboard.CampoConfirmarPassword, AutoSize = true, Location = new Point(24, y) };
            _txtConfirmar = new TextBox { Location = new Point(24, y + 20), Size = new Size(372, 26), PasswordChar = '●' };

            y += 56;
            var lblRol = new Label { Text = Textos.Dashboard.CampoRol, AutoSize = true, Location = new Point(24, y) };
            _cboRol = new ComboBox
            {
                Location = new Point(24, y + 20),
                Size = new Size(372, 26),
                DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(Sistemas.Core.Security.Models.RolDto.Nombre),
                ValueMember = nameof(Sistemas.Core.Security.Models.RolDto.Id)
            };

            y += 56;
            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                AutoSize = false,
                Size = new Size(372, 32),
                Location = new Point(24, y)
            };

            y += 36;
            _btnGuardar = new Button
            {
                Text = Textos.Dashboard.BotonGuardar,
                Location = new Point(24, y),
                Size = new Size(372, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;

            AcceptButton = _btnGuardar;

            Controls.AddRange(new Control[]
            {
                lblTitulo, lblSubtitulo,
                lblUsuario, _txtNombreUsuario,
                lblNombreCompleto, _txtNombreCompleto,
                lblPassword, _txtPassword,
                lblConfirmar, _txtConfirmar,
                lblRol, _cboRol,
                _lblError, _btnGuardar
            });

            Load += FormRegistro_Load;
        }

        private async void FormRegistro_Load(object? sender, EventArgs e)
        {
            try
            {
                var roles = await AuthService.ListarRolesAsync();
                _cboRol.DataSource = roles.ToList();
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSeConectoBdPrefijo + ex.Message);
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
                _lblError.Text = Textos.Dashboard.ErrorSeleccioneRol;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                var usuarioCreadorId = SessionContext.Current?.UsuarioId;
                var (exito, mensaje, _) = await AuthService.CrearUsuarioAsync(
                    nombreUsuario, nombreCompleto, password, rolId, usuarioCreadorId);

                if (exito)
                {
                    DialogResult = DialogResult.OK;
                    Close();
                }
                else
                {
                    _lblError.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSeConectoBdPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
