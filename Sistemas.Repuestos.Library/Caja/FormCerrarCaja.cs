using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Caja
{
    // Modal chico para cerrar la sesión de caja abierta. El monto esperado
    // que se muestra viene de sp_ObtenerMontoEsperadoCaja (solo lectura); la
    // diferencia final la calcula sp_CerrarCaja al confirmar — este
    // formulario nunca la calcula por su cuenta.
    public sealed class FormCerrarCaja : FormBase
    {
        private readonly int _sesionCajaId;

        private readonly Label _lblMontoEsperado;
        private readonly NumericUpDown _numEfectivoContado;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FormCerrarCaja(int sesionCajaId)
        {
            _sesionCajaId = sesionCajaId;

            Text = Textos.Caja.CerrarTitulo;
            ClientSize = new Size(340, 220);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            _lblMontoEsperado = new Label
            {
                AutoSize = true,
                Location = new Point(20, 16),
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Text = Textos.Caja.CalculandoMontoEsperado
            };

            var lblEfectivo = new Label { Text = Textos.Caja.CampoEfectivoContado, AutoSize = true, Location = new Point(20, 56) };
            _numEfectivoContado = new NumericUpDown { Location = new Point(20, 76), Size = new Size(160, 26), DecimalPlaces = 2, Maximum = 999999, Minimum = 0 };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(300, 60), Location = new Point(20, 110) };

            _btnGuardar = new Button
            {
                Text = Textos.Caja.BotonCerrarCaja,
                Location = new Point(20, 176),
                Size = new Size(300, 32),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            Controls.AddRange(new Control[] { _lblMontoEsperado, lblEfectivo, _numEfectivoContado, _lblError, _btnGuardar });

            Load += async (s, e) => await CargarMontoEsperadoAsync();
        }

        private async System.Threading.Tasks.Task CargarMontoEsperadoAsync()
        {
            try
            {
                var montoEsperado = await CajaService.ObtenerMontoEsperadoAsync(_sesionCajaId);
                _lblMontoEsperado.Text = string.Format(Textos.Caja.FormatoMontoEsperado, montoEsperado);
            }
            catch (Exception ex)
            {
                _lblMontoEsperado.Text = string.Empty;
                _lblError.Text = Textos.Caja.NoSeCargoMontoEsperadoPrefijo + ex.Message;
            }
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, montoCalculado, diferencia) = await CajaService.CerrarAsync(
                    _sesionCajaId, _numEfectivoContado.Value, SessionContext.Current?.UsuarioId ?? 0);

                if (exito)
                {
                    MostrarInfo(string.Format(Textos.Caja.FormatoResultadoCierre, mensaje, montoCalculado ?? 0, diferencia ?? 0));
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
                MostrarError(Textos.Caja.NoSeCerroCajaPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
