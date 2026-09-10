using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;

namespace Sistemas.Repuestos.Library.Cuentas
{
    // Diálogo de pago compartido por Cuentas por Cobrar y Cuentas por Pagar
    // — recibe el saldo pendiente y un delegado que llama al SP correcto
    // (sp_RegistrarPagoCuentaPorCobrar o ...PorPagar), para no duplicar el
    // formulario dos veces.
    public sealed class FormRegistrarPago : FormBase
    {
        private readonly Func<decimal, string?, Task<(bool Exito, string Mensaje)>> _registrarPago;

        private readonly NumericUpDown _numMonto;
        private readonly TextBox _txtMetodoPago;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FormRegistrarPago(decimal saldoPendiente, Func<decimal, string?, Task<(bool Exito, string Mensaje)>> registrarPago)
        {
            _registrarPago = registrarPago;

            Text = Textos.Cuentas.PagoFormularioTitulo;
            ClientSize = new Size(400, 280);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            var lblSaldo = new Label
            {
                Text = string.Format(Textos.Cuentas.PagoSaldoPendienteFormato, saldoPendiente),
                Dock = DockStyle.Top,
                Height = 28,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            var grilla = FormularioLayout.CrearGrilla();
            _numMonto = new NumericUpDown { Width = 160, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = saldoPendiente, Minimum = 0.01m, Value = saldoPendiente };
            FormularioLayout.AgregarCampo(grilla, Textos.Cuentas.CampoMontoAPagar, _numMonto);
            _txtMetodoPago = new TextBox { Width = 220, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Cuentas.CampoMetodoPago, _txtMetodoPago);

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 32,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Cuentas.BotonRegistrarPagoAccion);
            _btnGuardar.Dock = DockStyle.Bottom;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            pnlContenido.Controls.Add(_btnGuardar);
            pnlContenido.Controls.Add(_lblError);
            pnlContenido.Controls.Add(grilla);
            pnlContenido.Controls.Add(lblSaldo);
            Controls.Add(pnlContenido);
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            _btnGuardar.Enabled = false;
            try
            {
                var metodo = string.IsNullOrWhiteSpace(_txtMetodoPago.Text) ? null : _txtMetodoPago.Text.Trim();
                var (exito, mensaje) = await _registrarPago(_numMonto.Value, metodo);

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
                MostrarError(Textos.Cuentas.NoSeRegistroPagoPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
