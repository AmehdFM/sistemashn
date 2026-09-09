using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Sistemas.Core.Configuracion;
using Sistemas.Core.Configuracion.Models;
using Sistemas.Core.Files;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Common;

namespace Sistemas.Core.UI.Dashboard
{
    // Ajustes de la empresa, organizado en pestañas: General (datos y logo
    // del negocio), Facturación (CAI opcional) y Usuarios (solo para
    // administradores). Todas comparten un único botón "Guardar cambios"
    // fuera de las pestañas, porque General y Facturación escriben en la
    // misma fila de Configuracion.Configuracion.
    public sealed class AjustesControl : UserControl
    {
        private readonly TextBox _txtNombreComercial;
        private readonly TextBox _txtRTN;
        private readonly TextBox _txtDireccion;
        private readonly TextBox _txtTelefono;
        private readonly TextBox _txtCorreo;
        private readonly PictureBox _picLogo;
        private readonly CheckBox _chkRequiereFacturacionLegal;
        private readonly Button _btnConfigurarCai;
        private readonly Label _lblEstado;
        private readonly Button _btnGuardar;

        private string? _logoRutaActual;
        private byte[]? _logoNuevo;
        private string? _logoNuevaExtension;

        public AjustesControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var lblTitulo = new Label
            {
                Text = Textos.Dashboard.AjustesTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Location = new Point(32, 24),
                Dock = DockStyle.Top,
                Height = 56,
                Padding = new Padding(32, 20, 0, 0)
            };

            var tabs = new TabControl { Dock = DockStyle.Fill };

            // ============ Pestaña General ============
            var tabGeneral = new TabPage(Textos.Dashboard.TabGeneral) { AutoScroll = true };

            int y = 24;
            var lblNombre = new Label { Text = Textos.Dashboard.CampoNombreComercial, AutoSize = true, Location = new Point(24, y) };
            _txtNombreComercial = new TextBox { Location = new Point(24, y + 20), Size = new Size(360, 26) };

            y += 56;
            var lblRTN = new Label { Text = Textos.Dashboard.CampoRtnOpcional, AutoSize = true, Location = new Point(24, y) };
            _txtRTN = new TextBox { Location = new Point(24, y + 20), Size = new Size(200, 26), MaxLength = 14 };

            y += 56;
            var lblDireccion = new Label { Text = Textos.Dashboard.CampoDireccion, AutoSize = true, Location = new Point(24, y) };
            _txtDireccion = new TextBox { Location = new Point(24, y + 20), Size = new Size(360, 26) };

            y += 56;
            var lblTelefono = new Label { Text = Textos.Dashboard.CampoTelefono, AutoSize = true, Location = new Point(24, y) };
            _txtTelefono = new TextBox { Location = new Point(24, y + 20), Size = new Size(200, 26) };

            y += 56;
            var lblCorreo = new Label { Text = Textos.Dashboard.CampoCorreoContacto, AutoSize = true, Location = new Point(24, y) };
            _txtCorreo = new TextBox { Location = new Point(24, y + 20), Size = new Size(360, 26) };

            y += 56;
            var lblLogo = new Label { Text = Textos.Dashboard.CampoLogoNegocio, AutoSize = true, Location = new Point(24, y) };

            _picLogo = new PictureBox
            {
                Location = new Point(24, y + 20),
                Size = new Size(56, 56),
                BorderStyle = BorderStyle.FixedSingle,
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = UiTheme.FondoContenido
            };

            var btnCambiarLogo = new Button
            {
                Text = Textos.Dashboard.BotonCambiarLogo,
                Location = new Point(92, y + 24),
                Size = new Size(140, 30)
            };
            btnCambiarLogo.Click += BtnCambiarLogo_Click;

            tabGeneral.Controls.AddRange(new Control[]
            {
                lblNombre, _txtNombreComercial,
                lblRTN, _txtRTN,
                lblDireccion, _txtDireccion,
                lblTelefono, _txtTelefono,
                lblCorreo, _txtCorreo,
                lblLogo, _picLogo, btnCambiarLogo
            });

            // Editar el catálogo (crear/desactivar unidades) cambia cómo se
            // registran ventas/compras/inventario para todos — igual criterio
            // que la pestaña Usuarios, solo para administradores.
            if (SessionContext.Current?.EsAdministrador == true)
            {
                y += 92; // la fila del logo es más alta (PictureBox de 56px) que las demás
                var btnUnidadesMedida = new Button
                {
                    Text = Textos.Dashboard.BotonUnidadesMedida,
                    Location = new Point(24, y),
                    Size = new Size(180, 32)
                };
                btnUnidadesMedida.Click += (s, e) =>
                {
                    using var form = new FormUnidadesMedida();
                    form.ShowDialog(this.FindForm());
                };
                tabGeneral.Controls.Add(btnUnidadesMedida);
            }

            // ============ Pestaña Facturación ============
            var tabFacturacion = new TabPage(Textos.Dashboard.TabFacturacion) { AutoScroll = true };

            _chkRequiereFacturacionLegal = new CheckBox
            {
                Text = Textos.Dashboard.CampoRequiereFacturacionLegal,
                AutoSize = true,
                Location = new Point(24, 24)
            };

            _btnConfigurarCai = new Button
            {
                Text = Textos.Dashboard.BotonConfigurarCai,
                Location = new Point(24, 60),
                Size = new Size(180, 32),
                Enabled = false
            };
            _btnConfigurarCai.Click += (s, e) =>
            {
                using var form = new FormFacturacionCai();
                form.ShowDialog(this.FindForm());
            };
            _chkRequiereFacturacionLegal.CheckedChanged += (s, e) => _btnConfigurarCai.Enabled = _chkRequiereFacturacionLegal.Checked;

            tabFacturacion.Controls.AddRange(new Control[] { _chkRequiereFacturacionLegal, _btnConfigurarCai });

            tabs.TabPages.Add(tabGeneral);
            tabs.TabPages.Add(tabFacturacion);

            // ============ Pestaña Usuarios (solo administradores) ============
            if (SessionContext.Current?.EsAdministrador == true)
            {
                var tabUsuarios = new TabPage(Textos.Dashboard.TabUsuarios) { AutoScroll = true };

                var btnNuevoUsuario = new Button
                {
                    Text = Textos.Dashboard.BotonNuevoUsuario,
                    Location = new Point(24, 24),
                    Size = new Size(160, 32),
                    BackColor = UiTheme.Primario,
                    ForeColor = Color.White,
                    FlatStyle = FlatStyle.Flat
                };
                btnNuevoUsuario.FlatAppearance.BorderSize = 0;
                btnNuevoUsuario.Click += (s, e) =>
                {
                    using var registro = new FormRegistro();
                    registro.ShowDialog(this.FindForm());
                };

                tabUsuarios.Controls.Add(btnNuevoUsuario);
                tabs.TabPages.Add(tabUsuarios);
            }

            // ============ Pie compartido: estado + Guardar ============
            var pnlPie = new Panel { Dock = DockStyle.Bottom, Height = 76, BackColor = UiTheme.FondoContenido };

            _lblEstado = new Label
            {
                AutoSize = false,
                Size = new Size(600, 24),
                Location = new Point(32, 8)
            };

            _btnGuardar = new Button
            {
                Text = Textos.Dashboard.BotonGuardarCambios,
                Location = new Point(32, 34),
                Size = new Size(160, 32),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Enabled = false // se habilita cuando AjustesControl_Load termina de leer el estado actual
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;

            pnlPie.Controls.AddRange(new Control[] { _lblEstado, _btnGuardar });

            Controls.Add(tabs);
            Controls.Add(pnlPie);
            Controls.Add(lblTitulo);

            Load += AjustesControl_Load;
        }

        private async void AjustesControl_Load(object? sender, EventArgs e)
        {
            try
            {
                var config = await ConfiguracionService.ObtenerAsync();
                if (config.Existe)
                {
                    _txtNombreComercial.Text = config.NombreComercial;
                    _txtRTN.Text = config.RTN;
                    _txtDireccion.Text = config.Direccion;
                    _txtTelefono.Text = config.Telefono;
                    _txtCorreo.Text = config.CorreoContacto;
                    _chkRequiereFacturacionLegal.Checked = config.FacturacionLegalActiva;
                }

                _logoRutaActual = config.LogoRuta;
                var logoBytes = FileStorageService.Leer(_logoRutaActual);
                if (logoBytes is { Length: > 0 })
                {
                    // No se dispersa el MemoryStream: GDI+ puede decodificar la
                    // imagen de forma diferida y necesita el stream vivo mientras
                    // la Image esté en uso.
                    _picLogo.Image = Image.FromStream(new MemoryStream(logoBytes));
                }
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.Dashboard.NoSeCargoConfiguracionPrefijo + ex.Message;
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }

        private void BtnCambiarLogo_Click(object? sender, EventArgs e)
        {
            using var dialogo = new OpenFileDialog
            {
                Filter = Textos.Comun.FiltroImagenes,
                Title = Textos.Comun.TituloSeleccionarLogo
            };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                _logoNuevo = File.ReadAllBytes(dialogo.FileName);
                _logoNuevaExtension = Path.GetExtension(dialogo.FileName);
                _picLogo.Image = Image.FromStream(new MemoryStream(_logoNuevo));
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
                // Un logo nuevo se guarda en disco recién ahora, al confirmar
                // — así una selección que el usuario luego cancela (cierra
                // sin guardar) no deja archivos huérfanos en el almacén.
                var logoRutaAEnviar = _logoRutaActual;
                if (_logoNuevo != null)
                {
                    logoRutaAEnviar = FileStorageService.Guardar("Logos", _logoNuevo, _logoNuevaExtension ?? ".png");
                }

                var dto = new ConfiguracionDto
                {
                    NombreComercial = _txtNombreComercial.Text.Trim(),
                    RTN = rtn.Length == 0 ? null : rtn,
                    Direccion = _txtDireccion.Text.Trim(),
                    Telefono = _txtTelefono.Text.Trim(),
                    CorreoContacto = _txtCorreo.Text.Trim(),
                    LogoRuta = logoRutaAEnviar,
                    FacturacionLegalActiva = _chkRequiereFacturacionLegal.Checked
                };

                var (exito, mensaje) = await ConfiguracionService.GuardarAsync(dto, SessionContext.Current!.UsuarioId);
                if (exito)
                {
                    // El logo viejo ya no está referenciado por nadie: se
                    // elimina del disco para no acumular archivos huérfanos.
                    if (_logoNuevo != null && !string.IsNullOrEmpty(_logoRutaActual) && _logoRutaActual != logoRutaAEnviar)
                        FileStorageService.Eliminar(_logoRutaActual);

                    _logoRutaActual = logoRutaAEnviar;
                    _logoNuevo = null;
                    _logoNuevaExtension = null;
                }
                _lblEstado.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblEstado.Text = mensaje;
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
