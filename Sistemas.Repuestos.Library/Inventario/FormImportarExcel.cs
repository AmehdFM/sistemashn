using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;

namespace Sistemas.Repuestos.Library.Inventario
{
    public sealed class FormImportarExcel : FormBase
    {
        private readonly TextBox _txtRuta;
        private readonly Button _btnImportar;
        private readonly Label _lblResumen;
        private readonly DataGridView _grid;
        private string? _rutaSeleccionada;

        public FormImportarExcel()
        {
            Text = Textos.Inventario.ImportarTituloVentana;
            ClientSize = new Size(680, 520);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(560, 400);

            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 152, BackColor = Color.White };

            var lblInstrucciones = new Label
            {
                Text = Textos.Inventario.ImportarInstruccionesPrefijo + string.Join(", ", ProductService.EncabezadosImportacion),
                AutoSize = false,
                Size = new Size(640, 40),
                Location = new Point(16, 12)
            };

            _txtRuta = new TextBox { Location = new Point(16, 56), Size = new Size(460, 26), ReadOnly = true };
            var btnSeleccionar = new Button { Text = Textos.Inventario.BotonSeleccionarArchivo, Location = new Point(484, 55), Size = new Size(160, 28) };
            btnSeleccionar.Click += BtnSeleccionar_Click;

            _btnImportar = new Button
            {
                Text = Textos.Inventario.BotonImportar,
                Location = new Point(16, 96),
                Size = new Size(140, 32),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Enabled = false
            };
            _btnImportar.FlatAppearance.BorderSize = 0;
            _btnImportar.Click += BtnImportar_Click;

            _lblResumen = new Label { AutoSize = false, Size = new Size(500, 32), Location = new Point(168, 100) };

            pnlTop.Controls.AddRange(new Control[] { lblInstrucciones, _txtRuta, btnSeleccionar, _btnImportar, _lblResumen });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = "Codigo", HeaderText = "Código", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = "Exito", HeaderText = "Éxito", FillWeight = 10 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = "Accion", HeaderText = "Acción", FillWeight = 15 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = "Mensaje", HeaderText = "Mensaje", FillWeight = 55 });
            _grid.CellFormatting += Grid_CellFormatting;

            Controls.Add(_grid);
            Controls.Add(pnlTop);
        }

        private void Grid_CellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
        {
            if (_grid.Rows[e.RowIndex].DataBoundItem is Sistemas.Core.Inventory.Models.DetalleImportacionDto detalle && !detalle.Exito)
            {
                e.CellStyle!.BackColor = UiTheme.ErrorFondo;
                e.CellStyle.ForeColor = UiTheme.Error;
            }
        }

        private void BtnSeleccionar_Click(object? sender, EventArgs e)
        {
            using var dialogo = new OpenFileDialog { Filter = Textos.Comun.FiltroExcel };
            if (dialogo.ShowDialog(this) != DialogResult.OK) return;

            _rutaSeleccionada = dialogo.FileName;
            _txtRuta.Text = dialogo.FileName;
            _btnImportar.Enabled = true;
        }

        private async void BtnImportar_Click(object? sender, EventArgs e)
        {
            if (_rutaSeleccionada == null) return;

            _btnImportar.Enabled = false;
            _lblResumen.Text = Textos.Inventario.EstadoImportando;
            _lblResumen.ForeColor = UiTheme.TextoTenue;
            try
            {
                var usuarioId = SessionContext.Current?.UsuarioId ?? 0;
                var resultado = await ProductService.ImportarDesdeExcelAsync(_rutaSeleccionada, usuarioId);

                _lblResumen.ForeColor = resultado.FilasFallidas == 0 ? UiTheme.Primario : UiTheme.Error;
                _lblResumen.Text = resultado.Mensaje;
                _grid.DataSource = resultado.Detalle;
            }
            catch (Exception ex)
            {
                _lblResumen.ForeColor = UiTheme.Error;
                _lblResumen.Text = Textos.Inventario.NoSePudoImportarPrefijo + ex.Message;
            }
            finally
            {
                _btnImportar.Enabled = true;
            }
        }
    }
}
