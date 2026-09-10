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
        private const int Margen = 48;

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

            var pnlContenido = new Panel { Dock = DockStyle.Top, Padding = new Padding(Margen, UiTheme.Espacio.Xxl, Margen, 0), AutoSize = true };

            var pnlEncabezado = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 96, WrapContents = false, AutoSize = true, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg) };
            var pic = new PictureBox { Image = BrandingAssets.LogoCreador, SizeMode = PictureBoxSizeMode.Zoom, Size = new Size(96, 96), Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0) };
            var lblTitulo = new Label
            {
                Text = Textos.Arranque.PrimerUsuarioTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Margin = new Padding(0, (96 - (int)UiTheme.FuenteTitulo.GetHeight()) / 2, 0, 0)
            };
            pnlEncabezado.Controls.AddRange(new Control[] { pic, lblTitulo });
            pnlContenido.Resize += (s, e) => pnlEncabezado.Left = Math.Max(0, (pnlContenido.ClientSize.Width - pnlEncabezado.PreferredSize.Width) / 2);

            var lblSubtitulo = new Label
            {
                Text = Textos.Arranque.PrimerUsuarioSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                Dock = DockStyle.Top,
                Height = 24,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };

            var lblUsuario = new Label { Text = Textos.Dashboard.CampoNombreUsuario, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtNombreUsuario = new TextBox { Dock = DockStyle.Top, Height = 34, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblNombreCompleto = new Label { Text = Textos.Dashboard.CampoNombreCompleto, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtNombreCompleto = new TextBox { Dock = DockStyle.Top, Height = 34, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblPassword = new Label { Text = Textos.Dashboard.CampoPassword, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtPassword = new TextBox { Dock = DockStyle.Top, Height = 34, PasswordChar = '●', Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblConfirmar = new Label { Text = Textos.Dashboard.CampoConfirmarPassword, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtConfirmar = new TextBox { Dock = DockStyle.Top, Height = 34, PasswordChar = '●', Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            // Fijo en Administrador para el primer usuario, no se muestra.
            _cboRol = new ComboBox
            {
                Dock = DockStyle.Top,
                Height = 34,
                DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(Sistemas.Core.Security.Models.RolDto.Nombre),
                ValueMember = nameof(Sistemas.Core.Security.Models.RolDto.Id),
                Visible = false
            };

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 32,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            var pnlBoton = new Panel { Dock = DockStyle.Top, Height = 46 };
            _btnGuardar = new Button
            {
                Text = Textos.Arranque.PrimerUsuarioTitulo,
                Size = new Size(250, 46),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Anchor = AnchorStyles.Top
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;
            pnlBoton.Resize += (s, e) => _btnGuardar.Left = (pnlBoton.Width - _btnGuardar.Width) / 2;
            pnlBoton.Controls.Add(_btnGuardar);

            pnlContenido.Controls.Add(pnlBoton);
            pnlContenido.Controls.Add(_lblError);
            pnlContenido.Controls.Add(_cboRol);
            pnlContenido.Controls.Add(_txtConfirmar);
            pnlContenido.Controls.Add(lblConfirmar);
            pnlContenido.Controls.Add(_txtPassword);
            pnlContenido.Controls.Add(lblPassword);
            pnlContenido.Controls.Add(_txtNombreCompleto);
            pnlContenido.Controls.Add(lblNombreCompleto);
            pnlContenido.Controls.Add(_txtNombreUsuario);
            pnlContenido.Controls.Add(lblUsuario);
            pnlContenido.Controls.Add(lblSubtitulo);
            pnlContenido.Controls.Add(pnlEncabezado);

            Controls.Add(pnlContenido);

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
