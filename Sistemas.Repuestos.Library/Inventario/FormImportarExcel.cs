using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Export;
using Sistemas.Core.Inventory;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;

namespace Sistemas.Repuestos.Library.Inventario
{
    public sealed class FormImportarExcel : FormBase
    {
        private readonly Label _lblResumen;
        private readonly Button _btnSeleccionar;
        private readonly DataGridView _grid;

        public FormImportarExcel()
        {
            Text = Textos.Inventario.ImportarTituloVentana;
            ClientSize = new Size(680, 520);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(560, 400);

            var pnlSuperior = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var lblInstrucciones = new Label
            {
                Text = Textos.Inventario.ImportarInstruccionesPrefijo + string.Join(", ", ProductService.EncabezadosImportacion),
                Dock = DockStyle.Top,
                Height = 32,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm)
            };

            var pnlBotonPlantilla = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            var btnDescargarPlantilla = Botones.CrearSecundario(Textos.Inventario.BotonDescargarPlantilla);
            btnDescargarPlantilla.Click += BtnDescargarPlantilla_Click;
            pnlBotonPlantilla.Controls.Add(btnDescargarPlantilla);

            pnlSuperior.Controls.Add(pnlBotonPlantilla);
            pnlSuperior.Controls.Add(lblInstrucciones);

            // Botón central grande: seleccionar e importar es UN solo paso,
            // no dos — apenas se elige el archivo arranca la importación.
            var pnlCentro = new Panel { Dock = DockStyle.Top, Height = 120, BackColor = Color.White };
            _btnSeleccionar = Botones.CrearPrimario(Textos.Inventario.BotonSeleccionarArchivo);
            _btnSeleccionar.AutoSize = false;
            _btnSeleccionar.Size = new Size(260, 44);
            _btnSeleccionar.Anchor = AnchorStyles.Top;
            _btnSeleccionar.Click += BtnSeleccionar_Click;
            pnlCentro.Resize += (s, e) => _btnSeleccionar.Left = (pnlCentro.Width - _btnSeleccionar.Width) / 2;
            _btnSeleccionar.Top = UiTheme.Espacio.Xl;

            _lblResumen = new Label
            {
                Dock = DockStyle.Bottom,
                Height = 28,
                TextAlign = ContentAlignment.MiddleCenter
            };

            pnlCentro.Controls.Add(_lblResumen);
            pnlCentro.Controls.Add(_btnSeleccionar);

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = "Codigo", HeaderText = "Código", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = "Exito", HeaderText = "Éxito", FillWeight = 10 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = "Accion", HeaderText = "Acción", FillWeight = 15 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = "Mensaje", HeaderText = "Mensaje", FillWeight = 55 });
            _grid.CellFormatting += Grid_CellFormatting;

            Controls.Add(_grid);
            Controls.Add(pnlCentro);
            Controls.Add(pnlSuperior);
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
