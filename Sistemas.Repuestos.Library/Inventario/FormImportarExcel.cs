using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Export;
using Sistemas.Core.Inventory;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;

namespace Sistemas.Repuestos.Library.Inventario
{
    public sealed class FormImportarExcel : FormBase
    {
        private readonly Label _lblResumen;
        private readonly DataGridView _grid;

        public FormImportarExcel()
        {
            Text = Textos.Inventario.ImportarTituloVentana;
            ClientSize = new Size(680, 520);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(560, 400);

            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 168, BackColor = Color.White };

            var lblInstrucciones = new Label
            {
                Text = Textos.Inventario.ImportarInstruccionesPrefijo + string.Join(", ", ProductService.EncabezadosImportacion),
                AutoSize = false,
                Size = new Size(640, 32),
                Location = new Point(16, 12)
            };

            var btnDescargarPlantilla = new Button
            {
                Text = Textos.Inventario.BotonDescargarPlantilla,
                AutoSize = true,
                Padding = new Padding(14, 0, 14, 0),
                Height = 30,
                Location = new Point(16, 52)
            };
            btnDescargarPlantilla.Click += BtnDescargarPlantilla_Click;

            // Botón central grande: seleccionar e importar es UN solo paso,
            // no dos — apenas se elige el archivo arranca la importación.
            var btnSeleccionar = new Button
            {
                Text = Textos.Inventario.BotonSeleccionarArchivo,
                Size = new Size(260, 44),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            btnSeleccionar.FlatAppearance.BorderSize = 0;
            btnSeleccionar.Location = new Point((ClientSize.Width - btnSeleccionar.Width) / 2, 96);
            btnSeleccionar.Anchor = AnchorStyles.Top;
            btnSeleccionar.Click += BtnSeleccionar_Click;

            _lblResumen = new Label
            {
                AutoSize = false,
                TextAlign = ContentAlignment.MiddleCenter,
                Size = new Size(640, 24),
                Location = new Point(16, 144)
            };

            pnlTop.Controls.AddRange(new Control[] { lblInstrucciones, btnDescargarPlantilla, btnSeleccionar, _lblResumen });

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

        private void BtnDescargarPlantilla_Click(object? sender, EventArgs e)
        {
            using var dialogo = new SaveFileDialog { Filter = Textos.Comun.FiltroExcel, FileName = "plantilla_productos.xlsx" };
            if (dialogo.ShowDialog(this) != DialogResult.OK) return;

            try
            {
                ExcelExporter.GenerarPlantilla(dialogo.FileName, ProductService.EncabezadosImportacion, ProductService.FilasEjemploImportacion);
                MostrarInfo(Textos.Inventario.PlantillaGeneradaEnPrefijo + dialogo.FileName);
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Inventario.NoSeGeneroPlantillaPrefijo + ex.Message);
            }
        }

        private async void BtnSeleccionar_Click(object? sender, EventArgs e)
        {
            using var dialogo = new OpenFileDialog { Filter = Textos.Comun.FiltroExcel };
            if (dialogo.ShowDialog(this) != DialogResult.OK) return;

            var boton = (Button)sender!;
            boton.Enabled = false;
            _lblResumen.ForeColor = UiTheme.TextoTenue;
            _lblResumen.Text = Textos.Inventario.EstadoImportando;
            try
            {
                var usuarioId = SessionContext.Current?.UsuarioId ?? 0;
                var resultado = await ProductService.ImportarDesdeExcelAsync(dialogo.FileName, usuarioId);

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
                boton.Enabled = true;
            }
        }
    }
}
