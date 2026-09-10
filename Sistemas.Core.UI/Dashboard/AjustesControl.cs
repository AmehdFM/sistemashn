using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Sistemas.Core.Configuracion;
using Sistemas.Core.Configuracion.Models;
using Sistemas.Core.Files;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;

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
                Dock = DockStyle.Top,
                Height = 56,
                Padding = new Padding(UiTheme.Espacio.Xl, UiTheme.Espacio.Lg, 0, 0)
            };

            var tabs = new TabControl { Dock = DockStyle.Fill };

            // ============ Pestaña General ============
            var tabGeneral = new TabPage(Textos.Dashboard.TabGeneral) { AutoScroll = true, Padding = new Padding(UiTheme.Espacio.Xl) };

            var grilla = FormularioLayout.CrearGrilla();
            _txtNombreComercial = new TextBox { Width = 360, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoNombreComercial, _txtNombreComercial);
            _txtRTN = new TextBox { Width = 200, Height = UiTheme.Medidas.AlturaControl, MaxLength = 14 };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoRtnOpcional, _txtRTN);
            _txtDireccion = new TextBox { Width = 360, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoDireccion, _txtDireccion);
            _txtTelefono = new TextBox { Width = 200, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoTelefono, _txtTelefono);
            _txtCorreo = new TextBox { Width = 360, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Dashboard.CampoCorreoContacto, _txtCorreo);

            var pnlLogo = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg) };
            var lblLogo = new Label { Text = Textos.Dashboard.CampoLogoNegocio, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoTenue };
            _picLogo = new PictureBox
            {
                Size = new Size(56, 56),
                BorderStyle = BorderStyle.FixedSingle,
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = UiTheme.FondoContenido,
                Margin = new Padding(140, 0, UiTheme.Espacio.Md, 0)
            };
            var btnCambiarLogo = Botones.CrearSecundario(Textos.Dashboard.BotonCambiarLogo);
            btnCambiarLogo.Margin = new Padding(0, (56 - btnCambiarLogo.Height) / 2, 0, 0);
            btnCambiarLogo.Click += BtnCambiarLogo_Click;
            pnlLogo.Controls.AddRange(new Control[] { _picLogo, btnCambiarLogo });

            // Editar el catálogo (crear/desactivar unidades) cambia cómo se
            // registran ventas/compras/inventario para todos — igual criterio
            // que la pestaña Usuarios, solo para administradores. Se agrega
            // primero porque los controles Dock=Top se agregan del más
            // abajo (visualmente) al más arriba: el último agregado queda
            // más cerca del borde superior.
            if (SessionContext.Current?.EsAdministrador == true)
            {
                var btnUnidadesMedida = Botones.CrearSecundario(Textos.Dashboard.BotonUnidadesMedida);
                btnUnidadesMedida.Dock = DockStyle.Top;
                btnUnidadesMedida.Margin = new Padding(140, UiTheme.Espacio.Sm, 0, 0);
                btnUnidadesMedida.Click += (s, e) =>
                {
                    using var form = new FormUnidadesMedida();
                    form.ShowDialog(this.FindForm());
                };
                tabGeneral.Controls.Add(btnUnidadesMedida);
            }

            tabGeneral.Controls.Add(pnlLogo);
            tabGeneral.Controls.Add(lblLogo);
            tabGeneral.Controls.Add(grilla);

            // ============ Pestaña Facturación ============
            var tabFacturacion = new TabPage(Textos.Dashboard.TabFacturacion) { AutoScroll = true, Padding = new Padding(UiTheme.Espacio.Xl) };

            _chkRequiereFacturacionLegal = new CheckBox
            {
                Text = Textos.Dashboard.CampoRequiereFacturacionLegal,
                AutoSize = true,
                Dock = DockStyle.Top,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            _btnConfigurarCai = Botones.CrearSecundario(Textos.Dashboard.BotonConfigurarCai);
            _btnConfigurarCai.Dock = DockStyle.Top;
            _btnConfigurarCai.Enabled = false;
            _btnConfigurarCai.Click += (s, e) =>
            {
                using var form = new FormFacturacionCai();
                form.ShowDialog(this.FindForm());
            };
            _chkRequiereFacturacionLegal.CheckedChanged += (s, e) => _btnConfigurarCai.Enabled = _chkRequiereFacturacionLegal.Checked;

            tabFacturacion.Controls.Add(_btnConfigurarCai);
            tabFacturacion.Controls.Add(_chkRequiereFacturacionLegal);

            tabs.TabPages.Add(tabGeneral);
            tabs.TabPages.Add(tabFacturacion);

            // ============ Pestaña Usuarios (solo administradores) ============
            if (SessionContext.Current?.EsAdministrador == true)
            {
                var tabUsuarios = new TabPage(Textos.Dashboard.TabUsuarios) { AutoScroll = true, Padding = new Padding(UiTheme.Espacio.Xl) };

                var btnNuevoUsuario = Botones.CrearPrimario(Textos.Dashboard.BotonNuevoUsuario);
                btnNuevoUsuario.Dock = DockStyle.Top;
                btnNuevoUsuario.Click += (s, e) =>
                {
                    using var registro = new FormRegistro();
                    registro.ShowDialog(this.FindForm());
                };

                tabUsuarios.Controls.Add(btnNuevoUsuario);
                tabs.TabPages.Add(tabUsuarios);
            }

            // ============ Pie compartido: estado + Guardar ============
            var pnlPie = new Panel { Dock = DockStyle.Bottom, BackColor = UiTheme.FondoContenido, Padding = new Padding(UiTheme.Espacio.Xl, UiTheme.Espacio.Sm, UiTheme.Espacio.Xl, UiTheme.Espacio.Lg), AutoSize = true };

            _btnGuardar = Botones.CrearPrimario(Textos.Dashboard.BotonGuardarCambios);
            _btnGuardar.Dock = DockStyle.Top;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Width = 180;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 2;
            _btnGuardar.Margin = new Padding(0, UiTheme.Espacio.Sm, 0, 0);
            _btnGuardar.Enabled = false; // se habilita cuando AjustesControl_Load termina de leer el estado actual
            _btnGuardar.Click += BtnGuardar_Click;

            _lblEstado = new Label { Dock = DockStyle.Top, Height = 24 };

            pnlPie.Controls.Add(_btnGuardar);
            pnlPie.Controls.Add(_lblEstado);

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
