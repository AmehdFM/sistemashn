using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;

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
            ClientSize = new Size(360, 160);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;

            var lbl = new Label { Text = Textos.Inventario.CampoNombreCategoria, AutoSize = true, Location = new Point(20, 20) };
            _txtNombre = new TextBox { Location = new Point(20, 40), Size = new Size(320, 26) };

            _lblError = new Label
            {
                ForeColor = UiTheme.Error,
                AutoSize = false,
                Size = new Size(320, 32),
                Location = new Point(20, 74)
            };

            _btnGuardar = new Button
            {
                Text = Textos.Inventario.BotonCrear,
                Location = new Point(20, 112),
                Size = new Size(320, 32),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;
            AcceptButton = _btnGuardar;

            Controls.AddRange(new Control[] { lbl, _txtNombre, _lblError, _btnGuardar });
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
