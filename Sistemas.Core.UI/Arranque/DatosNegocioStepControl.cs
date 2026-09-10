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
        private const int Margen = 48;

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

            var pnlContenido = new Panel { Dock = DockStyle.Top, Padding = new Padding(Margen, UiTheme.Espacio.Xxl, Margen, 0), AutoSize = true };

            // Logo + título se centran como un solo grupo horizontal.
            var pnlEncabezado = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 96,
                WrapContents = false,
                AutoSize = true,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };
            var pic = new PictureBox { Image = BrandingAssets.LogoCreador, SizeMode = PictureBoxSizeMode.Zoom, Size = new Size(96, 96), Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0) };
            var lblTitulo = new Label
            {
                Text = Textos.Arranque.DatosNegocioTitulo,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Margin = new Padding(0, (96 - (int)UiTheme.FuenteTitulo.GetHeight()) / 2, 0, 0)
            };
            pnlEncabezado.Controls.AddRange(new Control[] { pic, lblTitulo });
            pnlContenido.Resize += (s, e) => pnlEncabezado.Left = Math.Max(0, (pnlContenido.ClientSize.Width - pnlEncabezado.PreferredSize.Width) / 2);

            var lblSubtitulo = new Label
            {
                Text = Textos.Arranque.DatosNegocioSubtitulo,
                ForeColor = UiTheme.TextoTenue,
                Dock = DockStyle.Top,
                Height = 36,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl)
            };

            var lblNombre = new Label { Text = Textos.Dashboard.CampoNombreComercial, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtNombreComercial = new TextBox { Dock = DockStyle.Top, Height = 32, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblRTN = new Label { Text = Textos.Dashboard.CampoRtnOpcional, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtRTN = new TextBox { Dock = DockStyle.Top, Width = 260, Height = 32, MaxLength = 14, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblDireccion = new Label { Text = Textos.Arranque.CampoDireccionOpcional, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtDireccion = new TextBox { Dock = DockStyle.Top, Height = 32, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblTelefono = new Label { Text = Textos.Arranque.CampoTelefonoOpcional, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtTelefono = new TextBox { Dock = DockStyle.Top, Width = 260, Height = 32, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblCorreo = new Label { Text = Textos.Arranque.CampoCorreoOpcional, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            _txtCorreo = new TextBox { Dock = DockStyle.Top, Height = 32, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var lblLogo = new Label { Text = Textos.Arranque.CampoLogoOpcional, ForeColor = UiTheme.TextoOscuro, Dock = DockStyle.Top, Height = 20 };
            var filaLogo = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xxl) };
            _picLogo = new PictureBox
            {
                Size = new Size(56, 56),
                BorderStyle = BorderStyle.FixedSingle,
                SizeMode = PictureBoxSizeMode.Zoom,
                BackColor = UiTheme.FondoContenido,
                Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0)
            };
            var btnSeleccionarLogo = new Button
            {
                Text = Textos.Arranque.BotonSeleccionarImagen,
                Size = new Size(180, 34),
                Cursor = Cursors.Hand,
                Margin = new Padding(0, (56 - 34) / 2, 0, 0)
            };
            btnSeleccionarLogo.Click += BtnSeleccionarLogo_Click;
            filaLogo.Controls.AddRange(new Control[] { _picLogo, btnSeleccionarLogo });

            _lblEstado = new Label
            {
                Dock = DockStyle.Top,
                Height = 32,
                TextAlign = ContentAlignment.TopCenter,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            var pnlBoton = new Panel { Dock = DockStyle.Top, Height = 46 };
            _btnGuardar = new Button
            {
                Text = Textos.Arranque.BotonContinuar,
                Size = new Size(200, 46),
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
            pnlContenido.Controls.Add(_lblEstado);
            pnlContenido.Controls.Add(filaLogo);
            pnlContenido.Controls.Add(lblLogo);
            pnlContenido.Controls.Add(_txtCorreo);
            pnlContenido.Controls.Add(lblCorreo);
            pnlContenido.Controls.Add(_txtTelefono);
            pnlContenido.Controls.Add(lblTelefono);
            pnlContenido.Controls.Add(_txtDireccion);
            pnlContenido.Controls.Add(lblDireccion);
            pnlContenido.Controls.Add(_txtRTN);
            pnlContenido.Controls.Add(lblRTN);
            pnlContenido.Controls.Add(_txtNombreComercial);
            pnlContenido.Controls.Add(lblNombre);
            pnlContenido.Controls.Add(lblSubtitulo);
            pnlContenido.Controls.Add(pnlEncabezado);

            Controls.Add(pnlContenido);
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
