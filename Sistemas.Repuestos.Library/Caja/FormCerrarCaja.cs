using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;
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
            ClientSize = new Size(360, 260);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            _lblMontoEsperado = new Label
            {
                Dock = DockStyle.Top,
                Height = 28,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                Text = Textos.Caja.CalculandoMontoEsperado,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            var grilla = FormularioLayout.CrearGrilla();
            _numEfectivoContado = new NumericUpDown { Width = 160, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = 999999, Minimum = 0 };
            FormularioLayout.AgregarCampo(grilla, Textos.Caja.CampoEfectivoContado, _numEfectivoContado);

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 50,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Caja.BotonCerrarCaja);
            _btnGuardar.Dock = DockStyle.Bottom;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            pnlContenido.Controls.Add(_btnGuardar);
            pnlContenido.Controls.Add(_lblError);
            pnlContenido.Controls.Add(grilla);
            pnlContenido.Controls.Add(_lblMontoEsperado);
            Controls.Add(pnlContenido);

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
