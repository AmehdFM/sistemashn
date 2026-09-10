using System.Drawing;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Terceros
{
    // Campos comunes de un Tercero (proveedor/cliente/ambos), reutilizados
    // tanto en el alta rápida (FormTercero) como en la edición completa
    // (FormPerfilTercero) — mismo control, mismo lugar de validación.
    //
    // Altura: Nombre(0-46) + Empresa(56-102) + Correo(112-158) +
    // Telefono(168-194) + RTN(168-194, columna derecha) + roles(224-244) +
    // _lblError(250-282) = 282px de contenido — Height se deja en 290 para
    // dejar un margen inferior y no repetir el bug de botones/labels
    // cortados por Height insuficiente que se corrigió en la revisión
    // visual anterior.
    public sealed class TerceroCamposControl : UserControl
    {
        private static readonly Regex CorreoFormatoBasico = new(@"^[^@\s]+@[^@\s]+\.[^@\s]+$", RegexOptions.Compiled);

        private readonly TextBox _txtNombre;
        private readonly TextBox _txtEmpresa;
        private readonly TextBox _txtCorreo;
        private readonly TextBox _txtTelefono;
        private readonly TextBox _txtRtn;
        private readonly CheckBox _chkEsProveedor;
        private readonly CheckBox _chkEsCliente;
        private readonly Label _lblError;

        public TerceroCamposControl()
        {
            Size = new Size(380, 290);

            var lblNombre = new Label { Text = Textos.Terceros.CampoNombre, AutoSize = true, Location = new Point(0, 0) };
            _txtNombre = new TextBox { Location = new Point(0, 20), Size = new Size(360, 26) };

            var lblEmpresa = new Label { Text = Textos.Terceros.CampoEmpresa, AutoSize = true, Location = new Point(0, 56) };
            _txtEmpresa = new TextBox { Location = new Point(0, 76), Size = new Size(360, 26) };

            var lblCorreo = new Label { Text = Textos.Terceros.CampoCorreo, AutoSize = true, Location = new Point(0, 112) };
            _txtCorreo = new TextBox { Location = new Point(0, 132), Size = new Size(360, 26) };

            var lblTelefono = new Label { Text = Textos.Terceros.CampoTelefono, AutoSize = true, Location = new Point(0, 168) };
            _txtTelefono = new TextBox { Location = new Point(0, 188), Size = new Size(170, 26) };

            var lblRtn = new Label { Text = Textos.Terceros.CampoRtnOpcional, AutoSize = true, Location = new Point(190, 168) };
            _txtRtn = new TextBox { Location = new Point(190, 188), Size = new Size(170, 26), MaxLength = 14 };

            _chkEsProveedor = new CheckBox { Text = Textos.Terceros.CampoEsProveedor, AutoSize = true, Location = new Point(0, 224) };
            _chkEsCliente = new CheckBox { Text = Textos.Terceros.CampoEsCliente, AutoSize = true, Location = new Point(190, 224) };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(360, 32), Location = new Point(0, 250) };

            Controls.AddRange(new Control[]
            {
                lblNombre, _txtNombre, lblEmpresa, _txtEmpresa, lblCorreo, _txtCorreo,
                lblTelefono, _txtTelefono, lblRtn, _txtRtn, _chkEsProveedor, _chkEsCliente, _lblError
            });
        }

        public void Cargar(TerceroDto tercero)
        {
            _txtNombre.Text = tercero.Nombre;
            _txtEmpresa.Text = tercero.Empresa;
            _txtCorreo.Text = tercero.Correo;
            _txtTelefono.Text = tercero.Telefono;
            _txtRtn.Text = tercero.RTN;
            _chkEsProveedor.Checked = tercero.EsProveedor;
            _chkEsCliente.Checked = tercero.EsCliente;
        }

        // Usado por el alta rápida: al crear desde "Proveedores" se
        // pre-marca EsProveedor, desde "Clientes" se pre-marca EsCliente —
        // ambos checkboxes quedan editables después.
        public void MarcarRolPorDefecto(bool esProveedor)
        {
            _chkEsProveedor.Checked = esProveedor;
            _chkEsCliente.Checked = !esProveedor;
        }

        public void MostrarError(string mensaje) => _lblError.Text = mensaje;

        public bool Validar(out string mensaje)
        {
            if (_txtNombre.Text.Trim().Length == 0)
            {
                mensaje = Textos.Terceros.ErrorNombreRequerido;
                _lblError.Text = mensaje;
                return false;
            }

            var rtn = _txtRtn.Text.Trim();
            if (rtn.Length > 0 && rtn.Length != 14)
            {
                mensaje = Textos.Terceros.ErrorRtnInvalido;
                _lblError.Text = mensaje;
                return false;
            }

            var correo = _txtCorreo.Text.Trim();
            if (correo.Length > 0 && !CorreoFormatoBasico.IsMatch(correo))
            {
                mensaje = Textos.Terceros.ErrorCorreoInvalido;
                _lblError.Text = mensaje;
                return false;
            }

            if (!_chkEsProveedor.Checked && !_chkEsCliente.Checked)
            {
                mensaje = Textos.Terceros.ErrorAlMenosUnRol;
                _lblError.Text = mensaje;
                return false;
            }

            mensaje = string.Empty;
            _lblError.Text = string.Empty;
            return true;
        }

        public (string Nombre, string? Empresa, string? Correo, string? Telefono, string? Rtn, bool EsProveedor, bool EsCliente) ObtenerValores()
        {
            return (
                _txtNombre.Text.Trim(),
                string.IsNullOrWhiteSpace(_txtEmpresa.Text) ? null : _txtEmpresa.Text.Trim(),
                string.IsNullOrWhiteSpace(_txtCorreo.Text) ? null : _txtCorreo.Text.Trim(),
                string.IsNullOrWhiteSpace(_txtTelefono.Text) ? null : _txtTelefono.Text.Trim(),
                string.IsNullOrWhiteSpace(_txtRtn.Text) ? null : _txtRtn.Text.Trim(),
                _chkEsProveedor.Checked,
                _chkEsCliente.Checked);
        }
    }
}
