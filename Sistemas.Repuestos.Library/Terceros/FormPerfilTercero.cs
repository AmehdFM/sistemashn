using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Repuestos.Library.Cuentas;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Terceros
{
    // Edición completa de un Tercero, con su panel de cuentas embebido
    // abajo: solo cuentas por pagar cuando se abre desde "Proveedores",
    // solo cuentas por cobrar cuando se abre desde "Clientes" — nunca
    // ambas, aunque el tercero tenga los dos roles a la vez.
    //
    // Altura del panel superior (pnlDatos): TerceroCamposControl (20-310) +
    // _chkActivo (318-338) + _btnGuardar (346-380) necesitan 380px de alto
    // más margen inferior de 16px = 396px — con menos, el botón Guardar
    // quedaba cortado por el borde del panel, el mismo bug ya corregido en
    // la revisión visual anterior. El panel de cuentas va Dock=Fill debajo,
    // así que crece con el form (que es redimensionable a propósito, a
    // diferencia del alta rápida).
    public sealed class FormPerfilTercero : FormBase
    {
        private const int AlturaPanelDatos = 396;

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

            var pnlDatos = new Panel { Dock = DockStyle.Top, Height = AlturaPanelDatos, BackColor = Color.White };

            _campos = new TerceroCamposControl { Location = new Point(20, 20) };
            _campos.Cargar(existente);

            _chkActivo = new CheckBox { Text = Textos.Comun.CampoActivo, AutoSize = true, Location = new Point(20, 318), Checked = existente.Activo };

            _btnGuardar = new Button
            {
                Text = Textos.Comun.BotonGuardar,
                Location = new Point(20, 346),
                Size = new Size(380, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;

            pnlDatos.Controls.Add(_campos);
            pnlDatos.Controls.Add(_chkActivo);
            pnlDatos.Controls.Add(_btnGuardar);

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
