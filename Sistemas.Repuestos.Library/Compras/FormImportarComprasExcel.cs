using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
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

            // Height = 152, igual que FormImportarExcel: mismos tres
            // controles apilados (instrucciones + selector, botón
            // importar + resumen), sin filas adicionales.
            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 152, BackColor = Color.White };

            var lblInstrucciones = new Label
            {
                Text = Textos.Compras.ImportarInstruccionesPrefijo + string.Join(", ", CompraService.EncabezadosImportacionCompras),
                AutoSize = false,
                Size = new Size(660, 40),
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

            _lblResumen = new Label { AutoSize = false, Size = new Size(520, 32), Location = new Point(168, 100) };

            pnlTop.Controls.AddRange(new Control[] { lblInstrucciones, _txtRuta, btnSeleccionar, _btnImportar, _lblResumen });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.Identificador), HeaderText = "Proveedor — Factura", FillWeight = 30 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.Exito), HeaderText = "Éxito", FillWeight = 10 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.CantidadLineas), HeaderText = "Líneas", FillWeight = 10 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(DetalleImportacionCompraDto.Mensaje), HeaderText = "Mensaje", FillWeight = 50 });
            _grid.CellFormatting += Grid_CellFormatting;

            Controls.Add(_grid);
            Controls.Add(pnlTop);
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
