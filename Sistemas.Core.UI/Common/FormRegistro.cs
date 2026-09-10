using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Controles;

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
            ClientSize = new Size(460, 480);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            var lblTitulo = new Label
            {
                Text = Textos.Dashboard.RegistroTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                Dock = DockStyle.Top,
                Height = 28,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xs)
            };

            var lblSubtitulo = new Label
            {
                Text = Textos.Dashboard.RegistroSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                Dock = DockStyle.Top,
                Height = 36,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl)
            };

            var grilla = FormularioLayout.CrearGrilla();
            _txtNombreUsuario = new TextBox { Width = 280, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoNombreUsuario, _txtNombreUsuario);
            _txtNombreCompleto = new TextBox { Width = 280, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoNombreCompleto, _txtNombreCompleto);
            _txtPassword = new TextBox { Width = 280, Height = UiTheme.Medidas.AlturaControl, PasswordChar = '●' };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoPassword, _txtPassword);
            _txtConfirmar = new TextBox { Width = 280, Height = UiTheme.Medidas.AlturaControl, PasswordChar = '●' };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoConfirmarPassword, _txtConfirmar);
            _cboRol = new ComboBox
            {
                Width = 280,
                Height = UiTheme.Medidas.AlturaControl,
                DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(Sistemas.Core.Security.Models.RolDto.Nombre),
                ValueMember = nameof(Sistemas.Core.Security.Models.RolDto.Id)
            };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoRol, _cboRol);

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 32,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Dashboard.BotonGuardar);
            _btnGuardar.Dock = DockStyle.Bottom;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            pnlContenido.Controls.Add(_btnGuardar);
            pnlContenido.Controls.Add(_lblError);
            pnlContenido.Controls.Add(grilla);
            pnlContenido.Controls.Add(lblSubtitulo);
            pnlContenido.Controls.Add(lblTitulo);
            Controls.Add(pnlContenido);

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
