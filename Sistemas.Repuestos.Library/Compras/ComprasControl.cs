using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Compras
{
    public sealed class ComprasControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly DataGridView _grid;
        private readonly EstadoListaControl _estado;
        private readonly PaginacionControl _paginacion;
        private EstadoLista _estadoActual;

        public ComprasControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(UiTheme.Espacio.Md)
            };

            var btnNuevaCompra = Botones.CrearToolbar(Textos.Compras.BotonNuevaCompra, primario: true);
            btnNuevaCompra.Click += BtnNuevaCompra_Click;
            var btnActualizar = Botones.CrearToolbar(Textos.Compras.BotonActualizar);
            btnActualizar.Click += async (s, e) => await CargarAsync();
            var btnImportar = Botones.CrearToolbar(Textos.Compras.BotonImportarExcel);
            btnImportar.Click += BtnImportar_Click;
            var btnExportar = Botones.CrearToolbar(Textos.Compras.BotonExportarExcel);
            btnExportar.Click += BtnExportar_Click;
            var btnPlantilla = Botones.CrearToolbar(Textos.Compras.BotonDescargarPlantilla);
            btnPlantilla.Click += BtnPlantilla_Click;

            pnlToolbar.Controls.AddRange(new Control[] { btnNuevaCompra, btnActualizar, btnImportar, btnExportar, btnPlantilla });

            _grid = new DataGridView { Visible = false };
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.Fecha), HeaderText = "Fecha", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.NombreProveedor), HeaderText = "Proveedor", FillWeight = 25 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.NumeroFacturaProveedor), HeaderText = "N° factura proveedor", FillWeight = 20 });
            var colTotal = new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.Total), HeaderText = "Total", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colTotal);
            _grid.Columns.Add(colTotal);
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(CompraDto.EsCredito), HeaderText = "Crédito", FillWeight = 10 });

            _estado = new EstadoListaControl();
            _estado.AccionSolicitada += async (s, e) =>
            {
                if (_estadoActual == EstadoLista.Error)
                    await CargarAsync();
                else
                    BtnNuevaCompra_Click(this, EventArgs.Empty);
            };

            var pnlGrid = new Panel { Dock = DockStyle.Fill };
            pnlGrid.Controls.Add(_grid);
            pnlGrid.Controls.Add(_estado);

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            Controls.Add(pnlGrid);
            Controls.Add(_paginacion);
            Controls.Add(pnlToolbar);

            Load += async (s, e) => await CargarAsync();
        }

        private async Task CargarAsync()
        {
            try
            {
                var (compras, total) = await CompraService.ListarAsync(null, _paginacion.Pagina, TamanoPagina);
                _paginacion.Actualizar(total, TamanoPagina);

                if (compras.Count == 0)
                {
                    _grid.Visible = false;
                    _estadoActual = EstadoLista.VacioInicial;
                    _estado.Mostrar(EstadoLista.VacioInicial, Textos.Compras.SinCompras, Textos.Compras.BotonNuevaCompra);
                    return;
                }

                _grid.DataSource = compras;
                _grid.Visible = true;
                _estado.Ocultar();
            }
            catch (Exception ex)
            {
                _grid.Visible = false;
                _estadoActual = EstadoLista.Error;
                _estado.Mostrar(EstadoLista.Error, Textos.Comun.NoSeConectoBdPrefijo + ex.Message, Textos.Comun.BotonReintentar);
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
