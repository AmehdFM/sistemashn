using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;

namespace Sistemas.Repuestos.Library.Inventario
{
    // Alta rápida de categoría (siempre de primer nivel — la gestión de
    // jerarquías completas queda fuera de alcance por ahora).
    public sealed class FormCategoriaRapida : FormBase
    {
        public int? CategoriaIdCreada { get; private set; }
        public string? NombreCreado { get; private set; }

        private readonly TextBox _txtNombre;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FormCategoriaRapida()
        {
            Text = Textos.Inventario.CategoriaRapidaTituloVentana;
            ClientSize = new Size(400, 200);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            var grilla = FormularioLayout.CrearGrilla();
            // Nombre/razón social: 280-360px según la guía UI/UX §3.
            _txtNombre = new TextBox { Width = 280, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grilla, Textos.Inventario.CampoNombreCategoria, _txtNombre);

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                Dock = DockStyle.Top,
                Height = 40,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md)
            };

            _btnGuardar = Botones.CrearPrimario(Textos.Inventario.BotonCrear);
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
            var nombre = _txtNombre.Text.Trim();
            if (nombre.Length == 0)
            {
                _lblError.Text = Textos.Inventario.ErrorNombreRequerido;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje, id) = await CategoryService.CrearAsync(nombre, null, SessionContext.Current?.UsuarioId);
                if (exito)
                {
                    CategoriaIdCreada = id;
                    NombreCreado = nombre;
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
                MostrarError(Textos.Inventario.NoSeCreoCategoriaPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
