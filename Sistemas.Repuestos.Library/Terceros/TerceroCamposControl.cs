using System.Text.RegularExpressions;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Terceros
{
    // Campos comunes de un Tercero (proveedor/cliente/ambos), reutilizados
    // tanto en el alta rápida (FormTercero) como en la edición completa
    // (FormPerfilTercero) — mismo control, mismo lugar de validación.
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
            AutoSize = true;
            AutoSizeMode = AutoSizeMode.GrowAndShrink;

            var grilla = FormularioLayout.CrearGrilla();
            _txtNombre = new TextBox { Width = 300, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Terceros.CampoNombre, _txtNombre);
            _txtEmpresa = new TextBox { Width = 300, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Terceros.CampoEmpresa, _txtEmpresa);
            _txtCorreo = new TextBox { Width = 300, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Terceros.CampoCorreo, _txtCorreo);
            _txtTelefono = new TextBox { Width = 180, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Terceros.CampoTelefono, _txtTelefono);
            _txtRtn = new TextBox { Width = 180, Height = UiTheme.Medidas.AlturaControl, MaxLength = 14 };
            FormularioLayout.AgregarCampo(grilla, Textos.Terceros.CampoRtnOpcional, _txtRtn);

            var pnlRoles = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(140, 0, 0, UiTheme.Espacio.Lg) };
            _chkEsProveedor = new CheckBox { Text = Textos.Terceros.CampoEsProveedor, AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0) };
            _chkEsCliente = new CheckBox { Text = Textos.Terceros.CampoEsCliente, AutoSize = true };
            pnlRoles.Controls.AddRange(new Control[] { _chkEsProveedor, _chkEsCliente });

            _lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 32 };

            Controls.Add(_lblError);
            Controls.Add(pnlRoles);
            Controls.Add(grilla);
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
