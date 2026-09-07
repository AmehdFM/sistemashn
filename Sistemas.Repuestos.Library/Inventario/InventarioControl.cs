using System;
using System.Drawing;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;

namespace Sistemas.Repuestos.Library.Inventario
{
    public sealed class InventarioControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly TextBox _txtBuscar;
        private readonly ComboBox _cboCategoria;
        private readonly CheckBox _chkSoloActivos;
        private readonly DataGridView _grid;
        private readonly PaginacionControl _paginacion;
        private readonly Label _lblEstado;

        public InventarioControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            // ---- Barra de herramientas ----
            var pnlToolbar = new Panel { Dock = DockStyle.Top, Height = 96, BackColor = Color.White };

            var btnNuevo = BotonToolbar(Textos.Comun.BotonNuevo, 12);
            btnNuevo.Click += async (s, e) => await AbrirFormularioAsync(null);

            var btnEditar = BotonToolbar(Textos.Comun.BotonEditar, 108);
            btnEditar.Click += async (s, e) =>
            {
                var seleccionado = ObtenerSeleccionado();
                if (seleccionado == null) { MessageBox.Show(this, Textos.Inventario.ErrorSeleccioneProductoPrimero, Textos.Inventario.TituloEditar); return; }
                await AbrirFormularioAsync(seleccionado);
            };

            var btnImportar = BotonToolbar(Textos.Inventario.BotonImportarExcel, 204);
            btnImportar.Click += BtnImportar_Click;

            var btnExportar = BotonToolbar(Textos.Inventario.BotonExportarExcel, 320);
            btnExportar.Click += BtnExportar_Click;

            var btnPlantilla = BotonToolbar(Textos.Inventario.BotonDescargarPlantilla, 436);
            btnPlantilla.Click += BtnPlantilla_Click;

            var btnArmarPaquete = BotonToolbar(Textos.Inventario.BotonArmarPaquete, 570);
            btnArmarPaquete.Click += BtnArmarPaquete_Click;

            var lblBuscar = new Label { Text = Textos.Comun.CampoBuscar, AutoSize = true, Location = new Point(12, 56) };
            _txtBuscar = new TextBox { Location = new Point(12, 72), Size = new Size(200, 26) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _paginacion.Reiniciar(); await CargarAsync(); } };

            var lblCategoria = new Label { Text = Textos.Inventario.CampoCategoria, AutoSize = true, Location = new Point(224, 56) };
            _cboCategoria = new ComboBox
            {
                Location = new Point(224, 72), Size = new Size(220, 26), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(CategoriaDto.Nombre), ValueMember = nameof(CategoriaDto.Id)
            };
            _cboCategoria.SelectedIndexChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            _chkSoloActivos = new CheckBox { Text = Textos.Comun.CampoSoloActivos, AutoSize = true, Location = new Point(456, 76), Checked = true };
            _chkSoloActivos.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(600, 71), Size = new Size(80, 28) };
            btnBuscar.Click += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            pnlToolbar.Controls.AddRange(new Control[]
            {
                btnNuevo, btnEditar, btnImportar, btnExportar, btnPlantilla, btnArmarPaquete,
                lblBuscar, _txtBuscar, lblCategoria, _cboCategoria, _chkSoloActivos, btnBuscar
            });

            // ---- Grid ----
            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.Codigo), HeaderText = "Código", FillWeight = 12 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.Nombre), HeaderText = "Nombre", FillWeight = 28 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.NombreCategoria), HeaderText = "Categoría", FillWeight = 16 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.PrecioUnitario), HeaderText = "Precio", FillWeight = 10, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.TasaISV), HeaderText = "ISV %", FillWeight = 8, DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.StockActual), HeaderText = "Stock", FillWeight = 8, DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ProductoDto.StockMinimo), HeaderText = "Stock mín.", FillWeight = 9, DefaultCellStyle = new DataGridViewCellStyle { Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(ProductoDto.Activo), HeaderText = "Activo", FillWeight = 7 });
            _grid.CellDoubleClick += async (s, e) =>
            {
                var seleccionado = ObtenerSeleccionado();
                if (seleccionado != null) await AbrirFormularioAsync(seleccionado);
            };

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            _lblEstado = new Label { Dock = DockStyle.Bottom, Height = 24, TextAlign = ContentAlignment.MiddleLeft, Padding = new Padding(12, 0, 0, 0), ForeColor = UiTheme.Error };

            Controls.Add(_grid);
            Controls.Add(_lblEstado);
            Controls.Add(_paginacion);
            Controls.Add(pnlToolbar);

            Load += async (s, e) => await InicializarAsync();
        }

        private static Button BotonToolbar(string texto, int x) => new()
        {
            Text = texto,
            Location = new Point(x, 12),
            Size = new Size(88, 32)
        };

        private async Task InicializarAsync()
        {
            try
            {
                var categorias = await CategoryService.ListarAsync();
                categorias.Insert(0, new CategoriaDto { Id = 0, Nombre = Textos.Inventario.CategoriaTodas });
                _cboCategoria.DataSource = categorias;
            }
            catch (Exception ex)
            {
                _lblEstado.Text = Textos.Inventario.NoSeCargaronCategoriasPrefijo + ex.Message;
            }

            await CargarAsync();
        }

        private async Task CargarAsync()
        {
            try
            {
                int? categoriaId = _cboCategoria.SelectedValue is int id && id > 0 ? id : null;
                var busqueda = string.IsNullOrWhiteSpace(_txtBuscar.Text) ? null : _txtBuscar.Text.Trim();

                var (productos, total) = await ProductService.ListarAsync(
                    _chkSoloActivos.Checked, categoriaId, busqueda, _paginacion.Pagina, TamanoPagina);

                _grid.DataSource = productos;
                _paginacion.Actualizar(total, TamanoPagina);
                _lblEstado.ForeColor = UiTheme.TextoTenue;
                _lblEstado.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private ProductoDto? ObtenerSeleccionado() => _grid.CurrentRow?.DataBoundItem as ProductoDto;

        private async Task AbrirFormularioAsync(ProductoDto? producto)
        {
            using var form = new FormProducto(producto);
            form.ShowDialog(FindForm());
            await CargarAsync();
        }

        private async void BtnImportar_Click(object? sender, EventArgs e)
        {
            using var form = new FormImportarExcel();
            form.ShowDialog(FindForm());
            await CargarAsync();
        }

        private async void BtnExportar_Click(object? sender, EventArgs e)
        {
            using var dialogo = new SaveFileDialog { Filter = Textos.Comun.FiltroExcel, FileName = "inventario.xlsx" };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                int? categoriaId = _cboCategoria.SelectedValue is int id && id > 0 ? id : null;
                var busqueda = string.IsNullOrWhiteSpace(_txtBuscar.Text) ? null : _txtBuscar.Text.Trim();
                var filas = await ProductService.ExportarAExcelAsync(dialogo.FileName, _chkSoloActivos.Checked, categoriaId, busqueda);
                MessageBox.Show(FindForm(), string.Format(Textos.Inventario.FormatoExportoOk, filas, dialogo.FileName), Textos.Inventario.TituloExportar);
            }
            catch (Exception ex)
            {
                MessageBox.Show(FindForm(), Textos.Inventario.NoSePudoExportarPrefijo + ex.Message, Sistemas.Core.UI.Textos.Comun.TituloError, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void BtnPlantilla_Click(object? sender, EventArgs e)
        {
            using var dialogo = new SaveFileDialog { Filter = Textos.Comun.FiltroExcel, FileName = "plantilla_productos.xlsx" };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                Sistemas.Core.Export.ExcelExporter.GenerarPlantilla(dialogo.FileName, ProductService.EncabezadosImportacion);
                MessageBox.Show(FindForm(), Textos.Inventario.PlantillaGeneradaEnPrefijo + dialogo.FileName, Textos.Inventario.TituloPlantilla);
            }
            catch (Exception ex)
            {
                MessageBox.Show(FindForm(), Textos.Inventario.NoSeGeneroPlantillaPrefijo + ex.Message, Sistemas.Core.UI.Textos.Comun.TituloError, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private async void BtnArmarPaquete_Click(object? sender, EventArgs e)
        {
            var seleccionado = ObtenerSeleccionado();
            if (seleccionado == null)
            {
                MessageBox.Show(this, Textos.Inventario.ErrorSeleccionePaqueteProducto, Textos.Inventario.TituloArmarPaquete);
                return;
            }

            using var form = new FormArmarPaquete(seleccionado);
            form.ShowDialog(FindForm());
            await CargarAsync();
        }
    }
}
