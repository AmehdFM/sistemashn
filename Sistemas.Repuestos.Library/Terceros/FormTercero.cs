using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Terceros
{
    // Alta rápida / edición chica de un Tercero. Reemplaza a FormProveedor.
    // Se usa desde TercerosControl ("Nuevo") y embebido como alta rápida en
    // el POS (botón "+" junto al combo de cliente).
    //
    // Altura: TerceroCamposControl (20-310) + _chkActivo (318-340) +
    // _btnGuardar (346-380) necesitan 380px de alto más margen inferior de
    // 20px — con menos el botón quedaba cortado por el borde del form,
    // el mismo bug ya corregido en la revisión visual anterior.
    public sealed class FormTercero : FormBase
    {
        private readonly int? _terceroId;
        private readonly TerceroCamposControl _campos;
        private readonly CheckBox _chkActivo;
        private readonly Button _btnGuardar;

        public int? TerceroIdGuardado { get; private set; }
        public string? NombreGuardado { get; private set; }

        public FormTercero(TerceroDto? existente, bool rolProveedorPorDefecto)
        {
            _terceroId = existente?.Id;

            var rol = rolProveedorPorDefecto ? Textos.Terceros.RolProveedorMinuscula : Textos.Terceros.RolClienteMinuscula;
            Text = string.Format(
                existente == null ? Textos.Terceros.FormularioTituloNuevoFormato : Textos.Terceros.FormularioTituloEditarFormato,
                rol);
            ClientSize = new Size(460, 440);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            _campos = new TerceroCamposControl { Dock = DockStyle.Top };

            _chkActivo = new CheckBox
            {
                Text = Textos.Comun.CampoActivo,
                AutoSize = true,
                Dock = DockStyle.Top,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg),
                Checked = true
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Comun.BotonGuardar);
            _btnGuardar.Dock = DockStyle.Bottom;
            _btnGuardar.AutoSize = false;
            _btnGuardar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            pnlContenido.Controls.Add(_btnGuardar);
            pnlContenido.Controls.Add(_chkActivo);
            pnlContenido.Controls.Add(_campos);
            Controls.Add(pnlContenido);

            if (existente != null)
            {
                _campos.Cargar(existente);
                _chkActivo.Checked = existente.Activo;
            }
            else
            {
                _campos.MarcarRolPorDefecto(rolProveedorPorDefecto);
            }
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            if (!_campos.Validar(out _))
                return;

            var (nombre, empresa, correo, telefono, rtn, esProveedor, esCliente) = _campos.ObtenerValores();

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, terceroId) = await TerceroService.GuardarAsync(
                    _terceroId, nombre, empresa, correo, telefono, rtn, esProveedor, esCliente,
                    _chkActivo.Checked, SessionContext.Current?.UsuarioId);

                if (exito)
                {
                    TerceroIdGuardado = terceroId;
                    NombreGuardado = nombre;
                    DialogResult = DialogResult.OK;
                    Close();
                }
                else
                {
                    _campos.MostrarError(mensaje);
                }
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
