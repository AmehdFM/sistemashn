using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Compras
{
    public sealed class ComprasControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly DataGridView _grid;
        private readonly PaginacionControl _paginacion;
        private readonly Label _lblEstado;

        public ComprasControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new Panel { Dock = DockStyle.Top, Height = 56, BackColor = Color.White };

            // Anchos por botón, no fijos iguales (mismo patrón que
            // Inventario/InventarioControl.cs): "Descargar plantilla"
            // necesita más espacio que "Nueva compra"/"Actualizar", cada
            // botón se posiciona a partir del borde derecho del anterior.
            const int gap = 8;
            int x = 12;

            var btnNuevaCompra = new Button { Text = Textos.Compras.BotonNuevaCompra, Location = new Point(x, 12), Size = new Size(140, 32), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnNuevaCompra.FlatAppearance.BorderSize = 0;
            btnNuevaCompra.Click += BtnNuevaCompra_Click;
            x += 140 + gap;

            var btnActualizar = BotonToolbar(Textos.Compras.BotonActualizar, x, 100);
            btnActualizar.Click += async (s, e) => await CargarAsync();
            x += 100 + gap;

            var btnImportar = BotonToolbar(Textos.Compras.BotonImportarExcel, x, 130);
            btnImportar.Click += BtnImportar_Click;
            x += 130 + gap;

            var btnExportar = BotonToolbar(Textos.Compras.BotonExportarExcel, x, 130);
            btnExportar.Click += BtnExportar_Click;
            x += 130 + gap;

            var btnPlantilla = BotonToolbar(Textos.Compras.BotonDescargarPlantilla, x, 170);
            btnPlantilla.Click += BtnPlantilla_Click;

            pnlToolbar.Controls.AddRange(new Control[] { btnNuevaCompra, btnActualizar, btnImportar, btnExportar, btnPlantilla });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.Fecha), HeaderText = "Fecha", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.NombreProveedor), HeaderText = "Proveedor", FillWeight = 25 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.NumeroFacturaProveedor), HeaderText = "N° factura proveedor", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.Total), HeaderText = "Total", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(CompraDto.EsCredito), HeaderText = "Crédito", FillWeight = 10 });

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            _lblEstado = new Label { Dock = DockStyle.Bottom, Height = 24, TextAlign = ContentAlignment.MiddleLeft, Padding = new Padding(12, 0, 0, 0), ForeColor = UiTheme.Error };

            Controls.Add(_grid);
            Controls.Add(_lblEstado);
            Controls.Add(_paginacion);
            Controls.Add(pnlToolbar);

            Load += async (s, e) => await CargarAsync();
        }

        private static Button BotonToolbar(string texto, int x, int ancho) => new()
        {
            Text = texto,
            Location = new Point(x, 12),
            Size = new Size(ancho, 32)
        };

        private async Task CargarAsync()
        {
            try
            {
                var (compras, total) = await CompraService.ListarAsync(null, _paginacion.Pagina, TamanoPagina);
                _grid.DataSource = compras;
                _paginacion.Actualizar(total, TamanoPagina);
                _lblEstado.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblEstado.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private async void BtnNuevaCompra_Click(object? sender, EventArgs e)
        {
            using var form = new FormRegistrarCompra();
            form.ShowDialog(FindForm());
            _paginacion.Reiniciar();
            await CargarAsync();
        }

        private async void BtnImportar_Click(object? sender, EventArgs e)
        {
            using var form = new FormImportarComprasExcel();
            form.ShowDialog(FindForm());
            _paginacion.Reiniciar();
            await CargarAsync();
        }

        private async void BtnExportar_Click(object? sender, EventArgs e)
        {
            using var dialogo = new SaveFileDialog { Filter = Textos.Comun.FiltroExcel, FileName = "compras.xlsx" };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                var filas = await CompraService.ExportarAExcelAsync(dialogo.FileName, null);
                MessageBox.Show(FindForm(), string.Format(Textos.Compras.FormatoExportoOk, filas, dialogo.FileName), Textos.Compras.TituloExportar);
            }
            catch (Exception ex)
            {
                MessageBox.Show(FindForm(), Textos.Compras.NoSePudoExportarPrefijo + ex.Message, Sistemas.Core.UI.Textos.Comun.TituloError, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private async void BtnPlantilla_Click(object? sender, EventArgs e)
        {
            using var dialogo = new SaveFileDialog { Filter = Textos.Comun.FiltroExcel, FileName = "plantilla_compras.xlsx" };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                await CompraService.GenerarPlantillaAsync(dialogo.FileName);
                MessageBox.Show(FindForm(), Textos.Compras.PlantillaGeneradaEnPrefijo + dialogo.FileName, Textos.Compras.TituloPlantilla);
            }
            catch (Exception ex)
            {
                MessageBox.Show(FindForm(), Textos.Compras.NoSeGeneroPlantillaPrefijo + ex.Message, Sistemas.Core.UI.Textos.Comun.TituloError, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
