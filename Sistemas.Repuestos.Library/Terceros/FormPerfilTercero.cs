using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Cuentas;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Terceros
{
    // Edición completa de un Tercero, con su panel de cuentas embebido
    // abajo: solo cuentas por pagar cuando se abre desde "Proveedores",
    // solo cuentas por cobrar cuando se abre desde "Clientes" — nunca
    // ambas, aunque el tercero tenga los dos roles a la vez. El panel de
    // datos es AutoSize (fluye con el contenido de TerceroCamposControl);
    // el panel de cuentas va Dock=Fill debajo y crece con el form
    // (redimensionable a propósito, a diferencia del alta rápida).
    public sealed class FormPerfilTercero : FormBase
    {
        private readonly int _terceroId;
        private readonly TerceroCamposControl _campos;
        private readonly CheckBox _chkActivo;
        private readonly Button _btnGuardar;

        public FormPerfilTercero(TerceroDto existente, bool vistaCuentasPorPagar)
        {
            _terceroId = existente.Id;

            var rol = vistaCuentasPorPagar ? Textos.Terceros.RolProveedorCapitalizado : Textos.Terceros.RolClienteCapitalizado;
            Text = string.Format(Textos.Terceros.PerfilTituloFormato, rol, existente.Nombre);
            ClientSize = new Size(700, 640);
            MinimumSize = new Size(640, 560);
            FormBorderStyle = FormBorderStyle.Sizable;
            MaximizeBox = true;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var pnlDatos = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Xl), AutoSize = true };

            _campos = new TerceroCamposControl { Dock = DockStyle.Top };
            _campos.Cargar(existente);

            _chkActivo = new CheckBox
            {
                Text = Textos.Comun.CampoActivo,
                AutoSize = true,
                Dock = DockStyle.Top,
                Checked = existente.Activo,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Comun.BotonGuardar);
            _btnGuardar.Dock = DockStyle.Top;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Width = 200;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;

            pnlDatos.Controls.Add(_btnGuardar);
            pnlDatos.Controls.Add(_chkActivo);
            pnlDatos.Controls.Add(_campos);

            Control panelCuentas = vistaCuentasPorPagar
                ? new CuentasPorPagarPanel(_terceroId)
                : new CuentasPorCobrarPanel(_terceroId);

            Controls.Add(panelCuentas);
            Controls.Add(pnlDatos);
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            if (!_campos.Validar(out _))
                return;

            var (nombre, empresa, correo, telefono, rtn, esProveedor, esCliente) = _campos.ObtenerValores();

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, _) = await TerceroService.GuardarAsync(
                    _terceroId, nombre, empresa, correo, telefono, rtn, esProveedor, esCliente,
                    _chkActivo.Checked, SessionContext.Current?.UsuarioId);

                if (exito)
                    MostrarInfo(mensaje);
                else
                    _campos.MostrarError(mensaje);
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoGuardarPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
