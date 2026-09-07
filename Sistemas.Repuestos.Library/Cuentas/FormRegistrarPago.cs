using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;

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
            ClientSize = new Size(360, 220);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var lblSaldo = new Label { Text = string.Format(Textos.Cuentas.PagoSaldoPendienteFormato, saldoPendiente), AutoSize = true, Location = new Point(20, 16), Font = new Font(UiTheme.FuenteBase, FontStyle.Bold) };

            var lblMonto = new Label { Text = Textos.Cuentas.CampoMontoAPagar, AutoSize = true, Location = new Point(20, 48) };
            _numMonto = new NumericUpDown { Location = new Point(20, 68), Size = new Size(160, 26), DecimalPlaces = 2, Maximum = saldoPendiente, Minimum = 0.01m, Value = saldoPendiente };

            var lblMetodo = new Label { Text = Textos.Cuentas.CampoMetodoPago, AutoSize = true, Location = new Point(20, 104) };
            _txtMetodoPago = new TextBox { Location = new Point(20, 124), Size = new Size(320, 26) };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(320, 24), Location = new Point(20, 154) };

            _btnGuardar = new Button
            {
                Text = Textos.Cuentas.BotonRegistrarPagoAccion,
                Location = new Point(20, 180),
                Size = new Size(320, 32),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            Controls.AddRange(new Control[] { lblSaldo, lblMonto, _numMonto, lblMetodo, _txtMetodoPago, _lblError, _btnGuardar });
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
