using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Facturacion;
using Sistemas.Core.Security;

namespace Sistemas.Core.UI.Dashboard
{
    // Configuración del CAI (facturación legal hondureña) — vive en Core,
    // no en una vertical: el requisito de facturar con CAI aplica por igual
    // a cualquier negocio, sin importar el rubro. Se accede desde la
    // pestaña "Facturación" de Ajustes, solo cuando el negocio activó el
    // interruptor de "Requiere facturación legal".
    public sealed class FacturacionCaiControl : UserControl
    {
        private readonly Label _lblEstadoActual;
        private readonly TextBox _txtRangoAutorizado;
        private readonly TextBox _txtRangoInicial;
        private readonly TextBox _txtRangoFinal;
        private readonly DateTimePicker _dtpAutorizacion;
        private readonly DateTimePicker _dtpVencimiento;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FacturacionCaiControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;
            AutoScroll = true;

            var pnlEstado = new Panel { Dock = DockStyle.Top, Height = 150, BackColor = Color.White };
            var lblTituloEstado = new Label { Text = Textos.Facturacion.TituloCaiActivo, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), AutoSize = true, Location = new Point(16, 12) };
            _lblEstadoActual = new Label { AutoSize = false, Size = new Size(600, 110), Location = new Point(16, 36), ForeColor = UiTheme.TextoTenue };
            pnlEstado.Controls.AddRange(new Control[] { lblTituloEstado, _lblEstadoActual });

            var pnlNuevo = new Panel { Dock = DockStyle.Top, Height = 300, BackColor = Color.White };
            var lblTituloNuevo = new Label { Text = Textos.Facturacion.TituloRegistrarNuevoCai, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), AutoSize = true, Location = new Point(16, 12) };

            var lblRangoAutorizado = new Label { Text = Textos.Facturacion.CampoRangoAutorizado, AutoSize = true, Location = new Point(16, 44) };
            _txtRangoAutorizado = new TextBox { Location = new Point(16, 64), Size = new Size(420, 26), MaxLength = 40 };

            var lblRangoInicial = new Label { Text = Textos.Facturacion.CampoRangoInicial, AutoSize = true, Location = new Point(16, 100) };
            _txtRangoInicial = new TextBox { Location = new Point(16, 120), Size = new Size(220, 26), MaxLength = 16 };

            var lblRangoFinal = new Label { Text = Textos.Facturacion.CampoRangoFinal, AutoSize = true, Location = new Point(250, 100) };
            _txtRangoFinal = new TextBox { Location = new Point(250, 120), Size = new Size(220, 26), MaxLength = 16 };

            var lblAutorizacion = new Label { Text = Textos.Facturacion.CampoFechaAutorizacion, AutoSize = true, Location = new Point(16, 156) };
            _dtpAutorizacion = new DateTimePicker { Location = new Point(16, 176), Size = new Size(160, 26), Format = DateTimePickerFormat.Short };

            var lblVencimiento = new Label { Text = Textos.Facturacion.CampoFechaVencimiento, AutoSize = true, Location = new Point(250, 156) };
            _dtpVencimiento = new DateTimePicker { Location = new Point(250, 176), Size = new Size(160, 26), Format = DateTimePickerFormat.Short, Value = DateTime.Today.AddYears(1) };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(600, 30), Location = new Point(16, 212) };

            _btnGuardar = new Button
            {
                Text = Textos.Facturacion.BotonRegistrarCai,
                Location = new Point(16, 246),
                Size = new Size(160, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;

            pnlNuevo.Controls.AddRange(new Control[]
            {
                lblTituloNuevo, lblRangoAutorizado, _txtRangoAutorizado,
                lblRangoInicial, _txtRangoInicial, lblRangoFinal, _txtRangoFinal,
                lblAutorizacion, _dtpAutorizacion, lblVencimiento, _dtpVencimiento,
                _lblError, _btnGuardar
            });

            Controls.Add(pnlNuevo);
            Controls.Add(pnlEstado);

            Load += async (s, e) => await CargarEstadoAsync();
        }

        private async System.Threading.Tasks.Task CargarEstadoAsync()
        {
            try
            {
                var config = await FacturacionService.ObtenerConfiguracionAsync();
                if (!config.Existe)
                {
                    _lblEstadoActual.ForeColor = UiTheme.Error;
                    _lblEstadoActual.Text = Textos.Facturacion.SinCaiConfigurado;
                    return;
                }

                string restantesTexto = Textos.Facturacion.RestantesSinDato;
                if (long.TryParse(config.CorrelativoActual, out var actual) && long.TryParse(config.RangoFinal, out var final))
                    restantesTexto = (final - actual).ToString("N0");

                _lblEstadoActual.ForeColor = UiTheme.TextoOscuro;
                _lblEstadoActual.Text = string.Format(Textos.Facturacion.EstadoFormato,
                    config.RangoAutorizado, config.RangoInicial, config.RangoFinal,
                    config.CorrelativoActual, restantesTexto, config.FechaAutorizacion, config.FechaVencimiento);
            }
            catch (Exception ex)
            {
                _lblEstadoActual.ForeColor = UiTheme.Error;
                _lblEstadoActual.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            var rangoAutorizado = _txtRangoAutorizado.Text.Trim();
            var rangoInicial = _txtRangoInicial.Text.Trim();
            var rangoFinal = _txtRangoFinal.Text.Trim();

            if (rangoAutorizado.Length == 0 || rangoInicial.Length != 16 || rangoFinal.Length != 16)
            {
                _lblError.Text = Textos.Facturacion.ErrorCamposRangoIncompletos;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje) = await FacturacionService.GuardarConfiguracionAsync(
                    rangoAutorizado, rangoInicial, rangoFinal,
                    _dtpAutorizacion.Value.Date, _dtpVencimiento.Value.Date,
                    SessionContext.Current?.UsuarioId);

                _lblError.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblError.Text = mensaje;

                if (exito)
                    await CargarEstadoAsync();
            }
            catch (Exception ex)
            {
                _lblError.ForeColor = UiTheme.Error;
                _lblError.Text = Textos.Comun.NoSeGuardoPrefijo + ex.Message;
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
