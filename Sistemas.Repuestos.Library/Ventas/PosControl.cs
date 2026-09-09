using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Ventas
{
    // Facturación rápida: buscar producto, armar el carrito y cobrar. El
    // historial de ventas (y anular una factura) vive aparte, en el módulo
    // "Ventas" (VentasControl) — POS se queda enfocado solo en cobrar rápido.
    public sealed class PosControl : UserControl
    {
        private readonly BindingList<LineaCarritoDto> _carrito = new();

        private readonly Panel _pnlVenta;
        private readonly TextBox _txtBuscar;
        private readonly CheckBox _chkPorEquivalencia;
        private readonly ComboBox _cboResultado;
        private readonly NumericUpDown _numCantidad;
        private readonly Label _lblUnidadSimbolo;
        private readonly DataGridView _gridCarrito;
        private readonly CheckBox _chkEsCredito;
        private readonly NumericUpDown _numDiasCredito;
        private readonly Label _lblTotal;
        private readonly Label _lblError;
        private readonly Button _btnCobrar;

        private readonly Panel _pnlResultado;
        private readonly Label _lblResumenFactura;

        private string? _ultimaFactura;
        private DateTime _ultimaFecha;
        private decimal _ultimoTotal;
        private System.Collections.Generic.List<LineaCarritoDto> _ultimasLineas = new();

        public PosControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            // ================= Panel de venta =================
            _pnlVenta = new Panel { Dock = DockStyle.Fill };

            var pnlBusqueda = new Panel { Dock = DockStyle.Top, Height = 116, BackColor = Color.White };

            var lblBuscar = new Label { Text = Textos.Pos.CampoBuscarProducto, AutoSize = true, Location = new Point(16, 8) };
            _txtBuscar = new TextBox { Location = new Point(16, 28), Size = new Size(220, 26) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; await BuscarAsync(); } };

            _chkPorEquivalencia = new CheckBox { Text = Textos.Pos.CampoBuscarPorEquivalencia, AutoSize = true, Location = new Point(246, 32) };

            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(16, 60), Size = new Size(100, 28) };
            btnBuscar.Click += async (s, e) => await BuscarAsync();

            _cboResultado = new ComboBox { Location = new Point(126, 60), Size = new Size(320, 28), DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true };
            _cboResultado.Format += (s, e) =>
            {
                e.Value = e.ListItem switch
                {
                    ProductoDto p => $"{p.Codigo} — {p.Nombre} (Stock: {CantidadFormatter.FormatearCantidad(p.StockActual, p.PermiteFraccionUnidad)} {p.UnidadMedidaSimbolo})",
                    EquivalenciaResultadoDto eq => $"{eq.Codigo} — {eq.Nombre} (Stock: {CantidadFormatter.FormatearCantidad(eq.StockActual, eq.PermiteFraccionUnidad)} {eq.UnidadMedidaSimbolo})",
                    _ => string.Empty
                };
            };
            _cboResultado.SelectedIndexChanged += (s, e) =>
            {
                var (permiteFraccion, simbolo) = _cboResultado.SelectedItem switch
                {
                    ProductoDto p => (p.PermiteFraccionUnidad, p.UnidadMedidaSimbolo),
                    EquivalenciaResultadoDto eq => (eq.PermiteFraccionUnidad, eq.UnidadMedidaSimbolo),
                    _ => (true, null)
                };
                CantidadFormatter.AplicarModoCantidad(_numCantidad, permiteFraccion);
                _lblUnidadSimbolo.Text = simbolo ?? string.Empty;
            };

            var lblCantidad = new Label { Text = Textos.Pos.CampoCantidadCorta, AutoSize = true, Location = new Point(456, 44) };
            _numCantidad = new NumericUpDown { Location = new Point(456, 60), Size = new Size(60, 28), Minimum = 1, Maximum = 10000, Value = 1 };
            _lblUnidadSimbolo = new Label { AutoSize = true, Location = new Point(456, 90), ForeColor = UiTheme.TextoTenue };

            var btnAgregar = new Button { Text = Textos.Pos.BotonAgregarAlCarrito, Location = new Point(526, 59), Size = new Size(140, 30), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnAgregar.FlatAppearance.BorderSize = 0;
            btnAgregar.Click += BtnAgregar_Click;

            pnlBusqueda.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, _chkPorEquivalencia, btnBuscar, _cboResultado, lblCantidad, _numCantidad, _lblUnidadSimbolo, btnAgregar });

            _gridCarrito = new DataGridView { DataSource = _carrito };
            GridStyler.Aplicar(_gridCarrito);
            _gridCarrito.AutoGenerateColumns = false;
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Codigo), HeaderText = "Código", FillWeight = 15 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Nombre), HeaderText = "Producto", FillWeight = 35 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.PrecioUnitarioReferencial), HeaderText = "Precio", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.SubtotalReferencial), HeaderText = "Subtotal", FillWeight = 20, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _gridCarrito.CellFormatting += (s, e) =>
            {
                if (_gridCarrito.Columns[e.ColumnIndex].DataPropertyName != nameof(LineaCarritoDto.Cantidad)) return;
                if (_carrito.Count <= e.RowIndex) return;
                var linea = _carrito[e.RowIndex];
                e.Value = CantidadFormatter.FormatearCantidad(linea.Cantidad, linea.PermiteFraccion);
                e.FormattingApplied = true;
            };

            var pnlPago = new Panel { Dock = DockStyle.Bottom, Height = 140, BackColor = Color.White };
            var btnQuitarLinea = new Button { Text = Textos.Pos.BotonQuitarLinea, Location = new Point(16, 8), Size = new Size(110, 28) };
            btnQuitarLinea.Click += (s, e) =>
            {
                if (_gridCarrito.CurrentRow?.DataBoundItem is LineaCarritoDto linea)
                {
                    _carrito.Remove(linea);
                    ActualizarTotal();
                }
            };

            _chkEsCredito = new CheckBox { Text = Textos.Pos.CampoVentaCredito, AutoSize = true, Location = new Point(16, 46) };
            _chkEsCredito.CheckedChanged += (s, e) => _numDiasCredito.Enabled = _chkEsCredito.Checked;
            var lblDias = new Label { Text = Textos.Pos.CampoDiasCredito, AutoSize = true, Location = new Point(150, 48) };
            _numDiasCredito = new NumericUpDown { Location = new Point(230, 46), Size = new Size(60, 26), Minimum = 1, Maximum = 365, Value = 15, Enabled = false };

            _lblTotal = new Label { Text = string.Format(Textos.Pos.FormatoTotal, 0m), AutoSize = true, Location = new Point(450, 44), Font = new Font(UiTheme.FuenteBase, FontStyle.Bold) };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(680, 30), Location = new Point(16, 78) };

            _btnCobrar = new Button
            {
                Text = Textos.Pos.BotonCobrar,
                Location = new Point(16, 108),
                Size = new Size(140, 30),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnCobrar.FlatAppearance.BorderSize = 0;
            _btnCobrar.Click += BtnCobrar_Click;

            pnlPago.Controls.AddRange(new Control[] { btnQuitarLinea, _chkEsCredito, lblDias, _numDiasCredito, _lblTotal, _lblError, _btnCobrar });

            _pnlVenta.Controls.Add(_gridCarrito);
            _pnlVenta.Controls.Add(pnlPago);
            _pnlVenta.Controls.Add(pnlBusqueda);

            // ================= Panel de resultado =================
            _pnlResultado = new Panel { Dock = DockStyle.Fill, Visible = false, BackColor = Color.White };
            _lblResumenFactura = new Label
            {
                AutoSize = false,
                Size = new Size(500, 160),
                Location = new Point(40, 40),
                Font = new Font(UiTheme.FuenteBase.FontFamily, 12f)
            };
            var btnImprimir = new Button { Text = Textos.Pos.BotonImprimir, Location = new Point(40, 210), Size = new Size(140, 34), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnImprimir.FlatAppearance.BorderSize = 0;
            btnImprimir.Click += async (s, e) =>
            {
                if (_ultimaFactura == null) return;

                string nombreNegocio;
                try
                {
                    var config = await Sistemas.Core.Configuracion.ConfiguracionService.ObtenerAsync();
                    nombreNegocio = config.Existe && !string.IsNullOrWhiteSpace(config.NombreComercial)
                        ? config.NombreComercial
                        : Textos.Pos.FacturaVentaGenerico;
                }
                catch
                {
                    nombreNegocio = Textos.Pos.FacturaVentaGenerico;
                }

                ReciboPrinter.Imprimir(nombreNegocio, _ultimaFactura, _ultimaFecha, _ultimoTotal, _ultimasLineas);
            };
            var btnNuevaVenta = new Button { Text = Textos.Pos.BotonNuevaVenta, Location = new Point(196, 210), Size = new Size(140, 34) };
            btnNuevaVenta.Click += (s, e) => MostrarPanelVenta();

            _pnlResultado.Controls.AddRange(new Control[] { _lblResumenFactura, btnImprimir, btnNuevaVenta });

            Controls.Add(_pnlVenta);
            Controls.Add(_pnlResultado);
        }

        private async System.Threading.Tasks.Task BuscarAsync()
        {
            var busqueda = _txtBuscar.Text.Trim();
            if (busqueda.Length == 0) return;

            try
            {
                if (_chkPorEquivalencia.Checked)
                {
                    var (resultados, _) = await RepuestoDetalleService.BuscarPorEquivalenciaAsync(busqueda, 1, 30);
                    _cboResultado.DataSource = resultados;
                }
                else
                {
                    var (productos, _) = await ProductService.ListarAsync(true, null, busqueda, 1, 30);
                    _cboResultado.DataSource = productos;
                }
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Comun.NoSePudoBuscarPrefijo + ex.Message;
            }
        }

        private void BtnAgregar_Click(object? sender, EventArgs e)
        {
            int productoId;
            string codigo, nombre;
            decimal precio;
            decimal tasaIsv;
            bool permiteFraccion;

            switch (_cboResultado.SelectedItem)
            {
                case ProductoDto p:
                    productoId = p.Id; codigo = p.Codigo; nombre = p.Nombre; precio = p.PrecioUnitario; tasaIsv = p.TasaISV; permiteFraccion = p.PermiteFraccionUnidad;
                    break;
                case EquivalenciaResultadoDto eq:
                    productoId = eq.Id; codigo = eq.Codigo; nombre = eq.Nombre; precio = eq.PrecioUnitario; tasaIsv = eq.TasaISV; permiteFraccion = eq.PermiteFraccionUnidad;
                    break;
                default:
                    _lblError.Text = Textos.Comun.ErrorBusqueSeleccioneProductoPrimero;
                    return;
            }

            var cantidad = _numCantidad.Value;
            var existente = _carrito.FirstOrDefault(l => l.ProductoId == productoId);
            if (existente != null)
            {
                existente.Cantidad += cantidad;
                _carrito.ResetItem(_carrito.IndexOf(existente));
            }
            else
            {
                _carrito.Add(new LineaCarritoDto
                {
                    ProductoId = productoId,
                    Codigo = codigo,
                    Nombre = nombre,
                    Cantidad = cantidad,
                    PermiteFraccion = permiteFraccion,
                    PrecioUnitarioReferencial = precio,
                    TasaISVReferencial = tasaIsv
                });
            }

            _lblError.Text = string.Empty;
            ActualizarTotal();
        }

        private void ActualizarTotal()
        {
            var subtotal = _carrito.Sum(l => l.SubtotalReferencial);
            var isv = _carrito.Sum(l => l.SubtotalReferencial * l.TasaISVReferencial / 100m);
            _lblTotal.Text = string.Format(Textos.Pos.FormatoTotal, subtotal + isv);
        }

        private async void BtnCobrar_Click(object? sender, EventArgs e)
        {
            if (_carrito.Count == 0)
            {
                _lblError.Text = Textos.Pos.ErrorCarritoVacio;
                return;
            }

            _btnCobrar.Enabled = false;
            try
            {
                var (exito, mensaje, numeroFactura, total) = await VentaService.RegistrarAsync(
                    _carrito.ToList(),
                    _chkEsCredito.Checked,
                    _chkEsCredito.Checked ? (int)_numDiasCredito.Value : null,
                    SessionContext.Current?.UsuarioId ?? 0);

                if (exito && numeroFactura != null && total.HasValue)
                {
                    _ultimaFactura = numeroFactura;
                    _ultimaFecha = DateTime.Now;
                    _ultimoTotal = total.Value;
                    _ultimasLineas = _carrito.ToList();

                    _lblResumenFactura.Text = string.Format(Textos.Pos.ResumenFacturaFormato, numeroFactura, _ultimaFecha, total.Value);

                    _pnlVenta.Visible = false;
                    _pnlResultado.Visible = true;
                }
                else
                {
                    _lblError.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Pos.NoSeRegistroVentaPrefijo + ex.Message;
            }
            finally
            {
                _btnCobrar.Enabled = true;
            }
        }

        private void MostrarPanelVenta()
        {
            _carrito.Clear();
            _chkEsCredito.Checked = false;
            _lblError.Text = string.Empty;
            ActualizarTotal();
            _pnlResultado.Visible = false;
            _pnlVenta.Visible = true;
        }
    }
}
