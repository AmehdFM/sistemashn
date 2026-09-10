using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Facturacion;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Controles;

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

            var pnlEstado = new Panel { Dock = DockStyle.Top, Height = 150, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg) };
            var lblTituloEstado = new Label { Text = Textos.Facturacion.TituloCaiActivo, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Dock = DockStyle.Top, Height = 24 };
            _lblEstadoActual = new Label { Dock = DockStyle.Fill, ForeColor = UiTheme.TextoTenue };
            pnlEstado.Controls.Add(_lblEstadoActual);
            pnlEstado.Controls.Add(lblTituloEstado);

            var pnlNuevo = new Panel { Dock = DockStyle.Top, Height = 340, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg) };
            var lblTituloNuevo = new Label { Text = Textos.Facturacion.TituloRegistrarNuevoCai, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md) };

            var grilla = FormularioLayout.CrearGrilla();
            _txtRangoAutorizado = new TextBox { Width = 320, Height = UiTheme.Medidas.AlturaControl, MaxLength = 40 };
            FormularioLayout.AgregarCampo(grilla, Textos.Facturacion.CampoRangoAutorizado, _txtRangoAutorizado);

            // Rango inicial/final y fechas autorización/vencimiento van en
            // par (guía UI/UX §8.1: dos columnas solo para campos cortos
            // con pares naturales).
            var filaRango = FilaDePar(
                Textos.Facturacion.CampoRangoInicial, _txtRangoInicial = new TextBox { Width = 190, Height = UiTheme.Medidas.AlturaControl, MaxLength = 16 },
                Textos.Facturacion.CampoRangoFinal, _txtRangoFinal = new TextBox { Width = 190, Height = UiTheme.Medidas.AlturaControl, MaxLength = 16 });

            var filaFechas = FilaDePar(
                Textos.Facturacion.CampoFechaAutorizacion, _dtpAutorizacion = new DateTimePicker { Width = 160, Height = UiTheme.Medidas.AlturaControl, Format = DateTimePickerFormat.Short },
                Textos.Facturacion.CampoFechaVencimiento, _dtpVencimiento = new DateTimePicker { Width = 160, Height = UiTheme.Medidas.AlturaControl, Format = DateTimePickerFormat.Short, Value = DateTime.Today.AddYears(1) });

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 30,
                Margin = new Padding(0, UiTheme.Espacio.Sm, 0, UiTheme.Espacio.Sm)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Facturacion.BotonRegistrarCai);
            _btnGuardar.Dock = DockStyle.Top;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Width = 200;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;

            pnlNuevo.Controls.Add(_btnGuardar);
            pnlNuevo.Controls.Add(_lblError);
            pnlNuevo.Controls.Add(filaFechas);
            pnlNuevo.Controls.Add(filaRango);
            pnlNuevo.Controls.Add(grilla);
            pnlNuevo.Controls.Add(lblTituloNuevo);

            Controls.Add(pnlNuevo);
            Controls.Add(pnlEstado);

            Load += async (s, e) => await CargarEstadoAsync();
        }

        // Fila de 2 campos lado a lado (etiqueta+control, etiqueta+control),
        // para los pares cortos que la guía permite en dos columnas.
        private static FlowLayoutPanel FilaDePar(string etiqueta1, Control control1, string etiqueta2, Control control2)
        {
            var fila = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };
            fila.Controls.Add(GrupoCampo(etiqueta1, control1));
            fila.Controls.Add(GrupoCampo(etiqueta2, control2));
            return fila;
        }

        private static Panel GrupoCampo(string etiqueta, Control control)
        {
            var lbl = new Label { Text = etiqueta, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoTenue };
            control.Dock = DockStyle.Top;
            var grupo = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0) };
            grupo.Controls.Add(control);
            grupo.Controls.Add(lbl);
            grupo.Width = control.Width;
            return grupo;
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
