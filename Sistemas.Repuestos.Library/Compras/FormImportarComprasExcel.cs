using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Compras
{
    // Clon estructural de Inventario/FormImportarExcel.cs — la única
    // diferencia real es la grilla de resultados, que muestra un resumen
    // por compra (Identificador/Exito/Mensaje/CantidadLineas) en vez de por
    // fila de producto (Codigo/Exito/Accion/Mensaje).
    public sealed class FormImportarComprasExcel : FormBase
    {
        private readonly TextBox _txtRuta;
        private readonly Button _btnImportar;
        private readonly Label _lblResumen;
        private readonly DataGridView _grid;
        private string? _rutaSeleccionada;

        public FormImportarComprasExcel()
        {
            Text = Textos.Compras.ImportarTituloVentana;
            ClientSize = new Size(700, 520);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(580, 400);

            var pnlSuperior = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var lblInstrucciones = new Label
            {
                Text = Textos.Compras.ImportarInstruccionesPrefijo + string.Join(", ", CompraService.EncabezadosImportacionCompras),
                Dock = DockStyle.Top,
                Height = 40,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm)
            };

            var pnlRuta = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md) };
            _txtRuta = new TextBox { Width = 420, Height = UiTheme.Medidas.AlturaControl, ReadOnly = true, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            var btnSeleccionar = Botones.CrearSecundario(Textos.Inventario.BotonSeleccionarArchivo);
            btnSeleccionar.Click += BtnSeleccionar_Click;
            pnlRuta.Controls.AddRange(new Control[] { _txtRuta, btnSeleccionar });

            var pnlImportar = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            _btnImportar = Botones.CrearPrimario(Textos.Inventario.BotonImportar);
            _btnImportar.Enabled = false;
            _btnImportar.Click += BtnImportar_Click;
            _lblResumen = new Label
            {
                AutoSize = false,
                Width = 480,
                Height = UiTheme.Medidas.AlturaControl,
                TextAlign = ContentAlignment.MiddleLeft,
                Margin = new Padding(UiTheme.Espacio.Md, 0, 0, 0)
            };
            pnlImportar.Controls.AddRange(new Control[] { _btnImportar, _lblResumen });

            pnlSuperior.Controls.Add(pnlImportar);
            pnlSuperior.Controls.Add(pnlRuta);
            pnlSuperior.Controls.Add(lblInstrucciones);

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.Identificador), HeaderText = "Proveedor — Factura", FillWeight = 30 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.Exito), HeaderText = "Éxito", FillWeight = 10 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.CantidadLineas), HeaderText = "Líneas", FillWeight = 10 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.Mensaje), HeaderText = "Mensaje", FillWeight = 50 });
            _grid.CellFormatting += Grid_CellFormatting;

            Controls.Add(_grid);
            Controls.Add(pnlSuperior);
        }

        private void Grid_CellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
        {
            if (_grid.Rows[e.RowIndex].DataBoundItem is DetalleImportacionCompraDto detalle && !detalle.Exito)
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
            _lblResumen.Text = Textos.Compras.EstadoImportando;
            _lblResumen.ForeColor = UiTheme.TextoTenue;
            try
            {
                var usuarioId = SessionContext.Current?.UsuarioId ?? 0;
                var resultado = await CompraService.ImportarDesdeExcelAsync(_rutaSeleccionada, usuarioId);

                _lblResumen.ForeColor = resultado.ComprasFallidas == 0 ? UiTheme.Primario : UiTheme.Error;
                _lblResumen.Text = resultado.Mensaje;
                _grid.DataSource = resultado.Detalle;
            }
            catch (Exception ex)
            {
                _lblResumen.ForeColor = UiTheme.Error;
                _lblResumen.Text = Textos.Compras.NoSePudoImportarPrefijo + ex.Message;
            }
            finally
            {
                _btnImportar.Enabled = true;
            }
        }
    }
}
