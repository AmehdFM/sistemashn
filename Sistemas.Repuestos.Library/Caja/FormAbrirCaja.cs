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
    // Modal chico para abrir una sesión de caja — mismo patrón que
    // Cuentas/FormRegistrarPago.cs (un campo numérico + Guardar). La
    // validación "ya hay una caja abierta" la hace sp_AbrirCaja, no aquí.
    public sealed class FormAbrirCaja : FormBase
    {
        private readonly NumericUpDown _numMontoApertura;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public int? SesionCajaIdCreada { get; private set; }

        public FormAbrirCaja()
        {
            Text = Textos.Caja.AbrirTitulo;
            ClientSize = new Size(360, 220);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            var grilla = FormularioLayout.CrearGrilla();
            _numMontoApertura = new NumericUpDown { Width = 160, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = 999999, Minimum = 0 };
            FormularioLayout.AgregarCampo(grilla, Textos.Caja.CampoMontoApertura, _numMontoApertura);

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 40,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Caja.BotonAbrirCaja);
            _btnGuardar.Dock = DockStyle.Bottom;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            pnlContenido.Controls.Add(_btnGuardar);
            pnlContenido.Controls.Add(_lblError);
            pnlContenido.Controls.Add(grilla);
            Controls.Add(pnlContenido);
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, sesionCajaId) = await CajaService.AbrirAsync(_numMontoApertura.Value, SessionContext.Current?.UsuarioId ?? 0);

                if (exito)
                {
                    SesionCajaIdCreada = sesionCajaId;
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
                MostrarError(Textos.Caja.NoSeAbrioCajaPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
