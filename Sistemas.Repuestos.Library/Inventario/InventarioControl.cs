using System;
using System.Collections.Generic;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.UI;

namespace Sistemas.Repuestos.Library.Inventario
{
    public sealed class InventarioControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly Panel _panelLista;
        private readonly Panel _panelDetalle;

        private readonly TextBox _txtBuscar;
        private readonly ComboBox _cboCategoria;
        private readonly CheckBox _chkSoloActivos;
        private readonly FlowLayoutPanel _panelCards;
        private readonly PaginacionControl _paginacion;
        private readonly Label _lblEstado;

        public InventarioControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            // ---- Barra de herramientas: solo Crear / Descargar / Cargar ----
            var pnlToolbar = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(12, 12, 12, 8)
            };

            var btnNuevo = BotonToolbar(Textos.Comun.BotonNuevo, primario: true);
            btnNuevo.Click += (s, e) => AbrirDetalle(null);

            var btnDescargar = BotonToolbar(Textos.Inventario.BotonExportarExcel);
            btnDescargar.Click += BtnDescargar_Click;

            var btnCargar = BotonToolbar(Textos.Inventario.BotonImportarExcel);
            btnCargar.Click += BtnCargar_Click;

            pnlToolbar.Controls.AddRange(new Control[] { btnNuevo, btnDescargar, btnCargar });

            // ---- Fila de filtros ----
            var pnlFiltros = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(12, 0, 12, 12)
            };

            var lblBuscar = new Label { Text = Textos.Comun.CampoBuscar, AutoSize = true, Margin = new Padding(0, 8, 6, 0) };
            _txtBuscar = new TextBox { Width = 200, Margin = new Padding(0, 4, 16, 0) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _paginacion.Reiniciar(); await CargarAsync(); } };

            var lblCategoria = new Label { Text = Textos.Inventario.CampoCategoria, AutoSize = true, Margin = new Padding(0, 8, 6, 0) };
            _cboCategoria = new ComboBox
            {
                Width = 200, Margin = new Padding(0, 4, 16, 0), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(CategoriaDto.Nombre), ValueMember = nameof(CategoriaDto.Id)
            };
            _cboCategoria.SelectedIndexChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            _chkSoloActivos = new CheckBox { Text = Textos.Comun.CampoSoloActivos, AutoSize = true, Checked = true, Margin = new Padding(0, 10, 16, 0) };
            _chkSoloActivos.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink, Padding = new Padding(12, 0, 12, 0), Height = 28, Margin = new Padding(0, 4, 0, 0) };
            btnBuscar.Click += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            pnlFiltros.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, lblCategoria, _cboCategoria, _chkSoloActivos, btnBuscar });

            // ---- Grilla de tarjetas ----
            _panelCards = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                WrapContents = true,
                BackColor = UiTheme.FondoContenido,
                Padding = new Padding(12)
            };

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            _lblEstado = new Label { Dock = DockStyle.Bottom, Height = 24, TextAlign = ContentAlignment.MiddleLeft, Padding = new Padding(12, 0, 0, 0), ForeColor = UiTheme.Error };

            _panelLista = new Panel { Dock = DockStyle.Fill };
            _panelLista.Controls.Add(_panelCards);
            _panelLista.Controls.Add(_lblEstado);
            _panelLista.Controls.Add(_paginacion);
            _panelLista.Controls.Add(pnlFiltros);
            _panelLista.Controls.Add(pnlToolbar);

            _panelDetalle = new Panel { Dock = DockStyle.Fill, Visible = false };

            Controls.Add(_panelLista);
            Controls.Add(_panelDetalle);

            Load += async (s, e) => await InicializarAsync();
        }

        private static Button BotonToolbar(string texto, bool primario = false)
        {
            var boton = new Button
            {
                Text = texto,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Padding = new Padding(14, 0, 14, 0),
                Height = 32,
                Margin = new Padding(0, 0, 8, 0)
            };
            if (primario)
            {
                boton.BackColor = UiTheme.Primario;
                boton.ForeColor = Color.White;
                boton.FlatStyle = FlatStyle.Flat;
                boton.FlatAppearance.BorderSize = 0;
            }
            return boton;
        }

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

                MostrarTarjetas(productos);
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

        private void MostrarTarjetas(List<ProductoDto> productos)
        {
            // Controls.Clear() no libera los controles removidos: hay que
            // disponerlos explícitamente o cada recarga deja tarjetas
            // huérfanas en memoria (mismo cuidado que FormDashboardBase al
            // cambiar de módulo).
            foreach (Control control in _panelCards.Controls)
                control.Dispose();
            _panelCards.Controls.Clear();

            if (productos.Count == 0)
            {
                _panelCards.Controls.Add(new Label
                {
                    Text = Textos.Inventario.SinProductos,
                    AutoSize = true,
                    ForeColor = UiTheme.TextoTenue,
                    Margin = new Padding(4, 12, 0, 0)
                });
                return;
            }

            foreach (var producto in productos)
            {
                var card = new ProductCard(producto);
                card.Click += (s, e) => AbrirDetalle(card.Producto);
                _panelCards.Controls.Add(card);
            }
        }

        // Un solo clic en la tarjeta ya abre el detalle en el mismo lugar
        // del grid — no hay más un botón "Editar" aparte ni un modo de
        // selección previo.
        private void AbrirDetalle(ProductoDto? producto)
        {
            var detalle = new ProductDetailControl(producto) { Dock = DockStyle.Fill };
            detalle.Volver += (s, e) => VolverALista(detalle);
            detalle.Guardado += async (s, e) => await CargarAsync();

            foreach (Control control in _panelDetalle.Controls)
                control.Dispose();
            _panelDetalle.Controls.Clear();
            _panelDetalle.Controls.Add(detalle);

            _panelLista.Visible = false;
            _panelDetalle.Visible = true;
        }

        private async void VolverALista(ProductDetailControl detalle)
        {
            _panelDetalle.Visible = false;
            _panelLista.Visible = true;

            _panelDetalle.Controls.Remove(detalle);
            detalle.Dispose();

            await CargarAsync();
        }

        private async void BtnDescargar_Click(object? sender, EventArgs e)
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

        private async void BtnCargar_Click(object? sender, EventArgs e)
        {
            using var form = new FormImportarExcel();
            form.ShowDialog(FindForm());
            await CargarAsync();
        }
    }
}
