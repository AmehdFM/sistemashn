using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Proveedores
{
    public sealed class FormProveedor : FormBase
    {
        private readonly int? _proveedorId;
        private readonly TextBox _txtNombre;
        private readonly TextBox _txtRtn;
        private readonly TextBox _txtTelefono;
        private readonly TextBox _txtContacto;
        private readonly CheckBox _chkActivo;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FormProveedor(ProveedorDto? proveedorExistente)
        {
            _proveedorId = proveedorExistente?.Id;

            Text = proveedorExistente == null ? Textos.Proveedores.FormularioTituloNuevo : Textos.Proveedores.FormularioTituloEditar;
            ClientSize = new Size(400, 360);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            int y = 20;
            var lblNombre = new Label { Text = Textos.Proveedores.CampoNombre, AutoSize = true, Location = new Point(20, y) };
            _txtNombre = new TextBox { Location = new Point(20, y + 20), Size = new Size(360, 26) };

            y += 56;
            var lblRtn = new Label { Text = Textos.Proveedores.CampoRtnOpcional, AutoSize = true, Location = new Point(20, y) };
            _txtRtn = new TextBox { Location = new Point(20, y + 20), Size = new Size(200, 26), MaxLength = 14 };

            y += 56;
            var lblTelefono = new Label { Text = Textos.Proveedores.CampoTelefono, AutoSize = true, Location = new Point(20, y) };
            _txtTelefono = new TextBox { Location = new Point(20, y + 20), Size = new Size(200, 26) };

            y += 56;
            var lblContacto = new Label { Text = Textos.Proveedores.CampoPersonaContacto, AutoSize = true, Location = new Point(20, y) };
            _txtContacto = new TextBox { Location = new Point(20, y + 20), Size = new Size(360, 26) };

            y += 56;
            _chkActivo = new CheckBox { Text = Textos.Comun.CampoActivo, AutoSize = true, Location = new Point(20, y), Checked = true };

            y += 32;
            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(360, 32), Location = new Point(20, y) };

            y += 36;
            _btnGuardar = new Button
            {
                Text = Textos.Comun.BotonGuardar,
                Location = new Point(20, y),
                Size = new Size(360, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            Controls.AddRange(new Control[]
            {
                lblNombre, _txtNombre, lblRtn, _txtRtn, lblTelefono, _txtTelefono,
                lblContacto, _txtContacto, _chkActivo, _lblError, _btnGuardar
            });

            if (proveedorExistente != null)
            {
                _txtNombre.Text = proveedorExistente.Nombre;
                _txtRtn.Text = proveedorExistente.RTN;
                _txtTelefono.Text = proveedorExistente.Telefono;
                _txtContacto.Text = proveedorExistente.Contacto;
                _chkActivo.Checked = proveedorExistente.Activo;
            }
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            var nombre = _txtNombre.Text.Trim();
            if (nombre.Length == 0)
            {
                _lblError.Text = Textos.Proveedores.ErrorNombreRequerido;
                return;
            }

            var rtn = _txtRtn.Text.Trim();
            if (rtn.Length > 0 && rtn.Length != 14)
            {
                _lblError.Text = Textos.Proveedores.ErrorRtnInvalido;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, _) = await ProveedorService.GuardarAsync(
                    _proveedorId,
                    nombre,
                    rtn.Length == 0 ? null : rtn,
                    string.IsNullOrWhiteSpace(_txtTelefono.Text) ? null : _txtTelefono.Text.Trim(),
                    string.IsNullOrWhiteSpace(_txtContacto.Text) ? null : _txtContacto.Text.Trim(),
                    _chkActivo.Checked,
                    SessionContext.Current?.UsuarioId);

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
                MostrarError(Textos.Comun.NoSePudoGuardarPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
