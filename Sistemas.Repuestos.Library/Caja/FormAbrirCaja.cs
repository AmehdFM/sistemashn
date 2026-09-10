using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
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
            ClientSize = new Size(340, 176);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var lblMonto = new Label { Text = Textos.Caja.CampoMontoApertura, AutoSize = true, Location = new Point(20, 16) };
            _numMontoApertura = new NumericUpDown { Location = new Point(20, 36), Size = new Size(160, 26), DecimalPlaces = 2, Maximum = 999999, Minimum = 0 };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(300, 40), Location = new Point(20, 70) };

            _btnGuardar = new Button
            {
                Text = Textos.Caja.BotonAbrirCaja,
                Location = new Point(20, 116),
                Size = new Size(300, 32),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            Controls.AddRange(new Control[] { lblMonto, _numMontoApertura, _lblError, _btnGuardar });
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
