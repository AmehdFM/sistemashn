using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
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

            var pnlBusqueda = new Panel { Dock = DockStyle.Top, Height = 116, BackColor = Color.White };

            var lblBuscar = new Label { Text = Textos.Pos.CampoBuscarProducto, AutoSize = true, Location = new Point(16, 8) };
            _txtBuscar = new TextBox { Location = new Point(16, 28), Size = new Size(220, 26) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; await BuscarOEscanearAsync(); } };

            // Y=8 (alineado con lblBuscar), no Y=32: el texto largo del
            // checkbox ("Buscar por número equivalente (OEM)") se extiende
            // más allá de x=456 y a Y=32 se solapaba con lblCantidad/
            // _numCantidad, que están en esa misma columna en la fila de
            // abajo.
            _chkPorEquivalencia = new CheckBox { Text = Textos.Pos.CampoBuscarPorEquivalencia, AutoSize = true, Location = new Point(246, 8) };

            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(16, 60), Size = new Size(100, 28) };
            btnBuscar.Click += async (s, e) => await BuscarAsync();

            _cboResultado = new ComboBox { Location = new Point(126, 60), Size = new Size(320, 28), DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true };
            _cboResultado.Format += (s, e) =>
            {
                e.Value = e.ListItem switch
                {
                    ProductoDto p => $"{p.Codigo} — {p.Nombre} (Stock: {p.StockActual})",
                    EquivalenciaResultadoDto eq => $"{eq.Codigo} — {eq.Nombre} (Stock: {eq.StockActual})",
                    _ => string.Empty
                };
            };

            var lblCantidad = new Label { Text = Textos.Pos.CampoCantidadCorta, AutoSize = true, Location = new Point(456, 44) };
            _numCantidad = new NumericUpDown { Location = new Point(456, 60), Size = new Size(60, 28), Minimum = 1, Maximum = 10000, Value = 1 };

            var btnAgregar = new Button { Text = Textos.Pos.BotonAgregarAlCarrito, Location = new Point(526, 59), Size = new Size(140, 30), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnAgregar.FlatAppearance.BorderSize = 0;
            btnAgregar.Click += BtnAgregar_Click;

            pnlBusqueda.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, _chkPorEquivalencia, btnBuscar, _cboResultado, lblCantidad, _numCantidad, btnAgregar });

            // ================= Aviso de caja cerrada =================
            // Oculto por defecto; se muestra en el Load si no hay sesión de
            // caja abierta y bloquea el cobro hasta que se abra ahí mismo.
            _pnlAvisoCaja = new Panel { Dock = DockStyle.Top, Height = 44, BackColor = UiTheme.ErrorFondo, Visible = false };
            _lblAvisoCaja = new Label { Text = Textos.Pos.AvisoCajaCerrada, AutoSize = true, ForeColor = UiTheme.Error, Location = new Point(16, 14) };
            _btnAbrirCajaDesdePos = new Button { Text = Textos.Pos.BotonAbrirCajaDesdePos, Location = new Point(460, 8), Size = new Size(120, 28), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            _btnAbrirCajaDesdePos.FlatAppearance.BorderSize = 0;
            _btnAbrirCajaDesdePos.Click += BtnAbrirCajaDesdePos_Click;
            _pnlAvisoCaja.Controls.AddRange(new Control[] { _lblAvisoCaja, _btnAbrirCajaDesdePos });

            _gridCarrito = new DataGridView { DataSource = _carrito };
            GridStyler.Aplicar(_gridCarrito);
            _gridCarrito.AutoGenerateColumns = false;
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Codigo), HeaderText = "Código", FillWeight = 15 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Nombre), HeaderText = "Producto", FillWeight = 35 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.PrecioUnitarioReferencial), HeaderText = "Precio", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _gridCarrito.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCarritoDto.SubtotalReferencial), HeaderText = "Subtotal", FillWeight = 20, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });

            // Height = 176 (antes 140): la fila de _cboMetodoPago se agregó
            // en Y=8/Y=44 al lado de cliente/crédito, y _lblError/_btnCobrar
            // se corrieron hacia abajo — con margen extra para no repetir
            // los bugs de layout de revisiones anteriores.
            var pnlPago = new Panel { Dock = DockStyle.Bottom, Height = 176, BackColor = Color.White };
            var btnQuitarLinea = new Button { Text = Textos.Pos.BotonQuitarLinea, Location = new Point(16, 8), Size = new Size(110, 28) };
            btnQuitarLinea.Click += (s, e) =>
            {
                if (_gridCarrito.CurrentRow?.DataBoundItem is LineaCarritoDto linea)
                {
                    _carrito.Remove(linea);
                    ActualizarTotal();
                }
            };

            var lblCliente = new Label { Text = Textos.Pos.CampoCliente, AutoSize = true, Location = new Point(142, 13) };
            _cboCliente = new ComboBox
            {
                Location = new Point(196, 9), Size = new Size(180, 26), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(TerceroDto.Nombre), ValueMember = nameof(TerceroDto.Id)
            };
            var btnNuevoCliente = new Button { Text = "+", Location = new Point(380, 8), Size = new Size(28, 28) };
            btnNuevoCliente.Click += BtnNuevoCliente_Click;

            var lblMetodoPago = new Label { Text = Textos.Pos.CampoMetodoPago, AutoSize = true, Location = new Point(420, 13) };
            _cboMetodoPago = new ComboBox { Location = new Point(420, 33), Size = new Size(140, 26), DropDownStyle = ComboBoxStyle.DropDownList };
            _cboMetodoPago.Items.AddRange(new object[] { Textos.Pos.MetodoPagoEfectivo, Textos.Pos.MetodoPagoTarjeta, Textos.Pos.MetodoPagoTransferencia });
            _cboMetodoPago.SelectedItem = Textos.Pos.MetodoPagoEfectivo;

            _chkEsCredito = new CheckBox { Text = Textos.Pos.CampoVentaCredito, AutoSize = true, Location = new Point(16, 68) };
            _chkEsCredito.CheckedChanged += (s, e) => _numDiasCredito.Enabled = _chkEsCredito.Checked;
            var lblDias = new Label { Text = Textos.Pos.CampoDiasCredito, AutoSize = true, Location = new Point(150, 70) };
            _numDiasCredito = new NumericUpDown { Location = new Point(230, 68), Size = new Size(60, 26), Minimum = 1, Maximum = 365, Value = 15, Enabled = false };

            _lblTotal = new Label { Text = string.Format(Textos.Pos.FormatoTotal, 0m), AutoSize = true, Location = new Point(420, 70), Font = new Font(UiTheme.FuenteBase, FontStyle.Bold) };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(680, 40), Location = new Point(16, 104) };

            _btnCobrar = new Button
            {
                Text = Textos.Pos.BotonCobrar,
                Location = new Point(16, 144),
                Size = new Size(140, 30),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnCobrar.FlatAppearance.BorderSize = 0;
            _btnCobrar.Click += BtnCobrar_Click;

            pnlPago.Controls.AddRange(new Control[]
            {
                btnQuitarLinea, lblCliente, _cboCliente, btnNuevoCliente, lblMetodoPago, _cboMetodoPago,
                _chkEsCredito, lblDias, _numDiasCredito, _lblTotal, _lblError, _btnCobrar
            });

            _pnlVenta.Controls.Add(_gridCarrito);
            _pnlVenta.Controls.Add(pnlPago);
            _pnlVenta.Controls.Add(_pnlAvisoCaja);
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

                ReciboPrinter.Imprimir(nombreNegocio, _ultimaFactura, _ultimaFecha, _ultimoTotal, _ultimasLineas, _ultimoEfectivoRecibido, _ultimoVuelto);
            };
            var btnNuevaVenta = new Button { Text = Textos.Pos.BotonNuevaVenta, Location = new Point(196, 210), Size = new Size(140, 34) };
            btnNuevaVenta.Click += (s, e) => MostrarPanelVenta();

            _pnlResultado.Controls.AddRange(new Control[] { _lblResumenFactura, btnImprimir, btnNuevaVenta });

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
                var (clientes, _) = await TerceroService.ListarClientesAsync(true, null, 1, 500);
                _cboCliente.DataSource = clientes;
                if (seleccionarId.HasValue)
                    _cboCliente.SelectedValue = seleccionarId.Value;
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
                        AgregarProductoAlCarrito(producto.Id, producto.Codigo, producto.Nombre, producto.PrecioUnitario, producto.TasaISV, (int)_numCantidad.Value);
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
            int stockActual;

            switch (_cboResultado.SelectedItem)
            {
                case ProductoDto p:
                    productoId = p.Id; codigo = p.Codigo; nombre = p.Nombre; precio = p.PrecioUnitario; tasaIsv = p.TasaISV; stockActual = p.StockActual;
                    break;
                case EquivalenciaResultadoDto eq:
                    productoId = eq.Id; codigo = eq.Codigo; nombre = eq.Nombre; precio = eq.PrecioUnitario; tasaIsv = eq.TasaISV; stockActual = eq.StockActual;
                    break;
                default:
                    _lblError.Text = Textos.Comun.ErrorBusqueSeleccioneProductoPrimero;
                    return;
            }

            AgregarProductoAlCarrito(productoId, codigo, nombre, precio, tasaIsv, (int)_numCantidad.Value);
            _lblError.Text = string.Empty;
        }

        // Mismo camino que usa BtnAgregar_Click para sumar/crear línea —
        // también lo usa el escaneo/tipeo de código de barras en
        // BuscarOEscanearAsync.
        private void AgregarProductoAlCarrito(int productoId, string codigo, string nombre, decimal precio, decimal tasaIsv, int cantidad)
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

        private async void MostrarPanelVenta()
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
