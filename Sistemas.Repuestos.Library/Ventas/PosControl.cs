using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Caja;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;
using Sistemas.Repuestos.Library.Terceros;

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
        private readonly ComboBox _cboCliente;
        private readonly CheckBox _chkEsCredito;
        private readonly NumericUpDown _numDiasCredito;
        private readonly ComboBox _cboMetodoPago;
        private readonly Label _lblTotal;
        private readonly Label _lblError;
        private readonly Button _btnCobrar;

        private readonly Panel _pnlAvisoCaja;
        private readonly Label _lblAvisoCaja;
        private readonly Button _btnAbrirCajaDesdePos;

        private readonly Panel _pnlResultado;
        private readonly Label _lblResumenFactura;

        private string? _ultimaFactura;
        private DateTime _ultimaFecha;
        private decimal _ultimoTotal;
        private decimal? _ultimoEfectivoRecibido;
        private decimal? _ultimoVuelto;
        private System.Collections.Generic.List<LineaCarritoDto> _ultimasLineas = new();

        public PosControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            // ================= Panel de venta =================
            _pnlVenta = new Panel { Dock = DockStyle.Fill };

            var pnlBusqueda = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var filaBuscar = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblBuscar = new Label { Text = Textos.Pos.CampoBuscarProducto, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            // El campo de búsqueda es el que recupera el foco tras cada
            // línea agregada (guía UI/UX §7.3, arquetipo Transacción/Captura):
            // código → Enter → cantidad → Enter → vuelve aquí.
            _txtBuscar = new TextBox { Width = 220, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; await BuscarOEscanearAsync(); } };
            _chkPorEquivalencia = new CheckBox { Text = Textos.Pos.CampoBuscarPorEquivalencia, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm + 2, 0, 0) };
            filaBuscar.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, _chkPorEquivalencia });

            var filaResultado = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            var btnBuscar = Botones.CrearSecundario(Textos.Comun.BotonBuscar);
            btnBuscar.Click += async (s, e) => await BuscarAsync();
            _cboResultado = new ComboBox { Width = 320, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
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

            var lblCantidad = new Label { Text = Textos.Pos.CampoCantidadCorta, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            _numCantidad = new NumericUpDown { Width = 70, Height = UiTheme.Medidas.AlturaControl, Minimum = 1, Maximum = 10000, Value = 1, Margin = new Padding(0, 0, UiTheme.Espacio.Xs, 0) };
            _lblUnidadSimbolo = new Label { AutoSize = true, ForeColor = UiTheme.TextoTenue, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Md, 0) };

            var btnAgregar = Botones.CrearPrimario(Textos.Pos.BotonAgregarAlCarrito);
            btnAgregar.Click += BtnAgregar_Click;

            filaResultado.Controls.AddRange(new Control[] { btnBuscar, _cboResultado, lblCantidad, _numCantidad, _lblUnidadSimbolo, btnAgregar });

            pnlBusqueda.Controls.Add(filaResultado);
            pnlBusqueda.Controls.Add(filaBuscar);

            // ================= Aviso de caja cerrada =================
            // Oculto por defecto; se muestra en el Load si no hay sesión de
            // caja abierta y bloquea el cobro hasta que se abra ahí mismo.
            _pnlAvisoCaja = new Panel { Dock = DockStyle.Top, Height = 44, BackColor = UiTheme.ErrorFondo, Visible = false, Padding = new Padding(UiTheme.Espacio.Lg, 0, UiTheme.Espacio.Lg, 0) };
            _lblAvisoCaja = new Label { Text = Textos.Pos.AvisoCajaCerrada, Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft, ForeColor = UiTheme.Error };
            _btnAbrirCajaDesdePos = Botones.CrearPrimario(Textos.Pos.BotonAbrirCajaDesdePos);
            _btnAbrirCajaDesdePos.Dock = DockStyle.Right;
            _btnAbrirCajaDesdePos.Margin = new Padding(0, UiTheme.Espacio.Xs, 0, UiTheme.Espacio.Xs);
            _btnAbrirCajaDesdePos.Click += BtnAbrirCajaDesdePos_Click;
            _pnlAvisoCaja.Controls.Add(_btnAbrirCajaDesdePos);
            _pnlAvisoCaja.Controls.Add(_lblAvisoCaja);

            _gridCarrito = new DataGridView { DataSource = _carrito };
            GridStyler.Aplicar(_gridCarrito);
            _gridCarrito.AutoGenerateColumns = false;
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Codigo), HeaderText = "Código", FillWeight = 15 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Nombre), HeaderText = "Producto", FillWeight = 35 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });
            var colPrecio = new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.PrecioUnitarioReferencial), HeaderText = "Precio", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colPrecio);
            _gridCarrito.Columns.Add(colPrecio);
            var colSubtotal = new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.SubtotalReferencial), HeaderText = "Subtotal", FillWeight = 20 };
            GridStyler.ComoColumnaNumerica(colSubtotal);
            _gridCarrito.Columns.Add(colSubtotal);
            _gridCarrito.CellFormatting += (s, e) =>
            {
                if (_gridCarrito.Columns[e.ColumnIndex].DataPropertyName != nameof(LineaCarritoDto.Cantidad)) return;
                if (_carrito.Count <= e.RowIndex) return;
                var linea = _carrito[e.RowIndex];
                e.Value = CantidadFormatter.FormatearCantidad(linea.Cantidad, linea.PermiteFraccion);
                e.FormattingApplied = true;
            };

            var pnlPago = new Panel { Dock = DockStyle.Bottom, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var filaClientePago = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var btnQuitarLinea = Botones.CrearSecundario(Textos.Pos.BotonQuitarLinea);
            btnQuitarLinea.Click += (s, e) =>
            {
                if (_gridCarrito.CurrentRow?.DataBoundItem is LineaCarritoDto linea)
                {
                    _carrito.Remove(linea);
                    ActualizarTotal();
                }
            };
            var lblCliente = new Label { Text = Textos.Pos.CampoCliente, AutoSize = true, Margin = new Padding(UiTheme.Espacio.Xl, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _cboCliente = new ComboBox
            {
                Width = 180, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(TerceroDto.Nombre), ValueMember = nameof(TerceroDto.Id),
                Margin = new Padding(0, 0, UiTheme.Espacio.Xs, 0)
            };
            var btnNuevoCliente = Botones.CrearSecundario("+");
            btnNuevoCliente.Width = 30;
            btnNuevoCliente.Margin = new Padding(0, 0, UiTheme.Espacio.Xl, 0);
            btnNuevoCliente.Click += BtnNuevoCliente_Click;
            var lblMetodoPago = new Label { Text = Textos.Pos.CampoMetodoPago, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _cboMetodoPago = new ComboBox { Width = 140, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList };
            _cboMetodoPago.Items.AddRange(new object[] { Textos.Pos.MetodoPagoEfectivo, Textos.Pos.MetodoPagoTarjeta, Textos.Pos.MetodoPagoTransferencia });
            _cboMetodoPago.SelectedItem = Textos.Pos.MetodoPagoEfectivo;
            filaClientePago.Controls.AddRange(new Control[] { btnQuitarLinea, lblCliente, _cboCliente, btnNuevoCliente, lblMetodoPago, _cboMetodoPago });

            var filaCreditoTotal = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            _chkEsCredito = new CheckBox { Text = Textos.Pos.CampoVentaCredito, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm + 4, UiTheme.Espacio.Md, 0) };
            _chkEsCredito.CheckedChanged += (s, e) => _numDiasCredito.Enabled = _chkEsCredito.Checked;
            var lblDias = new Label { Text = Textos.Pos.CampoDiasCredito, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm + 4, UiTheme.Espacio.Xs, 0) };
            _numDiasCredito = new NumericUpDown { Width = 60, Height = UiTheme.Medidas.AlturaControl, Minimum = 1, Maximum = 365, Value = 15, Enabled = false, Margin = new Padding(0, 0, UiTheme.Espacio.Xxl, 0) };
            // El total es la tipografía más grande de toda la pantalla
            // (guía UI/UX §7.3, arquetipo Transacción/Captura) — es lo
            // primero que el cajero y el cliente necesitan ver claro.
            _lblTotal = new Label { Text = string.Format(Textos.Pos.FormatoTotal, 0m), AutoSize = true, Font = new Font(UiTheme.FuenteTitulo.FontFamily, 18f, FontStyle.Bold) };
            filaCreditoTotal.Controls.AddRange(new Control[] { _chkEsCredito, lblDias, _numDiasCredito, _lblTotal });

            _lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 36, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            // Atajo de teclado visible en el botón (guía UI/UX §13): el
            // cajero puede cobrar sin tocar el mouse.
            _btnCobrar = Botones.CrearPrimario(Textos.Pos.BotonCobrar);
            _btnCobrar.AutoSize = false;
            _btnCobrar.Width = 160;
            _btnCobrar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnCobrar.Click += BtnCobrar_Click;

            pnlPago.Controls.Add(_btnCobrar);
            pnlPago.Controls.Add(_lblError);
            pnlPago.Controls.Add(filaCreditoTotal);
            pnlPago.Controls.Add(filaClientePago);

            _pnlVenta.Controls.Add(_gridCarrito);
            _pnlVenta.Controls.Add(pnlPago);
            _pnlVenta.Controls.Add(_pnlAvisoCaja);
            _pnlVenta.Controls.Add(pnlBusqueda);

            // ================= Panel de resultado =================
            _pnlResultado = new Panel { Dock = DockStyle.Fill, Visible = false, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Xxl) };
            _lblResumenFactura = new Label
            {
                Dock = DockStyle.Top,
                Height = 160,
                Font = new Font(UiTheme.FuenteBase.FontFamily, 12f),
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };
            var pnlAccionesResultado = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            var btnImprimir = Botones.CrearPrimario(Textos.Pos.BotonImprimir);
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

                ReciboPrinter.Imprimir(nombreNegocio, _ultimaFactura, _ultimaFecha, _ultimoTotal, _ultimasLineas, _ultimoEfectivoRecibido, _ultimoVuelto);
            };
            var btnNuevaVenta = Botones.CrearSecundario(Textos.Pos.BotonNuevaVenta);
            btnNuevaVenta.Click += async (s, e) => await MostrarPanelVenta();
            pnlAccionesResultado.Controls.AddRange(new Control[] { btnImprimir, btnNuevaVenta });

            _pnlResultado.Controls.Add(pnlAccionesResultado);
            _pnlResultado.Controls.Add(_lblResumenFactura);

            Controls.Add(_pnlVenta);
            Controls.Add(_pnlResultado);

            Load += async (s, e) =>
            {
                await CargarClientesAsync(null);
                await VerificarCajaAsync();
            };
        }

        private async System.Threading.Tasks.Task VerificarCajaAsync()
        {
            try
            {
                var sesionAbierta = await CajaService.ObtenerAbiertaAsync();
                var hayCaja = sesionAbierta != null;
                _pnlAvisoCaja.Visible = !hayCaja;
                _btnCobrar.Enabled = hayCaja;
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Pos.NoSeVerificoCajaPrefijo + ex.Message;
            }
        }

        private async void BtnAbrirCajaDesdePos_Click(object? sender, EventArgs e)
        {
            using var form = new FormAbrirCaja();
            if (form.ShowDialog(FindForm()) == DialogResult.OK)
                await VerificarCajaAsync();
        }

        private async System.Threading.Tasks.Task CargarClientesAsync(int? seleccionarId)
        {
            try
            {
                var (clientes, totalClientes) = await TerceroService.ListarClientesAsync(true, null, 1, 500);
                _cboCliente.DataSource = clientes;
                if (seleccionarId.HasValue)
                    _cboCliente.SelectedValue = seleccionarId.Value;

                // El combo carga hasta 500 filas de una vez: si el negocio
                // tiene más clientes activos que eso, se avisa en vez de
                // truncar en silencio (el resto sigue accesible por el
                // buscador de la pantalla de Clientes).
                if (totalClientes > clientes.Count)
                    _lblError.Text = string.Format(Textos.Pos.AvisoTopeClientesFormato, totalClientes);
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Pos.NoSeCargaronClientesPrefijo + ex.Message;
            }
        }

        private async void BtnNuevoCliente_Click(object? sender, EventArgs e)
        {
            using var form = new FormTercero(null, rolProveedorPorDefecto: false);
            if (form.ShowDialog(FindForm()) == DialogResult.OK && form.TerceroIdGuardado.HasValue)
                await CargarClientesAsync(form.TerceroIdGuardado);
        }

        // Intenta primero un match exacto de código de barras/código (para
        // que un lector USB, que solo "teclea" el código + Enter, agregue
        // directo al carrito sin hardware especial). Si no hay match exacto
        // — o si el cajero está buscando por equivalencia OEM, modo que no
        // se toca — cae al comportamiento de búsqueda parcial de siempre.
        private async System.Threading.Tasks.Task BuscarOEscanearAsync()
        {
            var busqueda = _txtBuscar.Text.Trim();
            if (busqueda.Length == 0) return;

            if (!_chkPorEquivalencia.Checked)
            {
                try
                {
                    var producto = await ProductService.BuscarPorCodigoExactoAsync(busqueda);
                    if (producto != null)
                    {
                        AgregarProductoAlCarrito(producto.Id, producto.Codigo, producto.Nombre, producto.PrecioUnitario, producto.TasaISV, _numCantidad.Value, producto.PermiteFraccionUnidad);
                        _txtBuscar.Clear();
                        _lblError.Text = string.Empty;
                        return;
                    }
                }
                catch (Exception ex)
                {
                    _lblError.Text = Textos.Comun.NoSePudoBuscarPrefijo + ex.Message;
                    return;
                }
            }

            await BuscarAsync();
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

            AgregarProductoAlCarrito(productoId, codigo, nombre, precio, tasaIsv, _numCantidad.Value, permiteFraccion);
            _lblError.Text = string.Empty;
        }

        // Mismo camino que usa BtnAgregar_Click para sumar/crear línea —
        // también lo usa el escaneo/tipeo de código de barras en
        // BuscarOEscanearAsync.
        private void AgregarProductoAlCarrito(int productoId, string codigo, string nombre, decimal precio, decimal tasaIsv, decimal cantidad, bool permiteFraccion)
        {
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

            var clienteId = _cboCliente.SelectedValue is int idCliente ? idCliente : (int?)null;
            if (_chkEsCredito.Checked && clienteId == null)
            {
                _lblError.Text = Textos.Pos.ErrorSeleccioneClienteCredito;
                return;
            }

            var metodoPago = (string)_cboMetodoPago.SelectedItem!;
            decimal? efectivoRecibido = null;

            // Solo el método Efectivo pasa por la calculadora de cambio —
            // Tarjeta/Transferencia se registran directo, sin modal, con
            // EfectivoRecibido en null (no afectan el cálculo de caja).
            if (metodoPago == Textos.Pos.MetodoPagoEfectivo)
            {
                var totalEstimado = _carrito.Sum(l => l.SubtotalReferencial) + _carrito.Sum(l => l.SubtotalReferencial * l.TasaISVReferencial / 100m);
                using var formCobro = new FormCobroEfectivo(totalEstimado);
                if (formCobro.ShowDialog(FindForm()) != DialogResult.OK)
                    return; // El cajero canceló: no se cobra nada.

                efectivoRecibido = formCobro.EfectivoRecibido;
            }

            _btnCobrar.Enabled = false;
            try
            {
                var (exito, mensaje, numeroFactura, total, efectivoRecibidoConfirmado, vuelto) = await VentaService.RegistrarAsync(
                    _carrito.ToList(),
                    _chkEsCredito.Checked,
                    _chkEsCredito.Checked ? (int)_numDiasCredito.Value : null,
                    SessionContext.Current?.UsuarioId ?? 0,
                    clienteId,
                    metodoPago,
                    efectivoRecibido);

                if (exito && numeroFactura != null && total.HasValue)
                {
                    _ultimaFactura = numeroFactura;
                    _ultimaFecha = DateTime.Now;
                    _ultimoTotal = total.Value;
                    // El efectivo recibido/vuelto que se guarda para el
                    // recibo es el que devolvió sp_RegistrarVenta — nunca el
                    // que calculó FormCobroEfectivo en pantalla.
                    _ultimoEfectivoRecibido = efectivoRecibidoConfirmado;
                    _ultimoVuelto = vuelto;
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

        private async System.Threading.Tasks.Task MostrarPanelVenta()
        {
            _carrito.Clear();
            _chkEsCredito.Checked = false;
            _cboCliente.SelectedIndex = -1;
            _cboMetodoPago.SelectedItem = Textos.Pos.MetodoPagoEfectivo;
            _lblError.Text = string.Empty;
            ActualizarTotal();
            _pnlResultado.Visible = false;
            _pnlVenta.Visible = true;
            await VerificarCajaAsync();
        }
    }
}
