using System;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Inventario
{
    // Crear/editar producto. Las pestañas de detalle de repuesto, vehículos
    // compatibles, equivalencias OEM y proveedores/precios solo se habilitan
    // en modo edición porque necesitan un ProductoId ya existente.
    public sealed class FormProducto : FormBase
    {
        private int? _productoId;
        private readonly int? _categoriaIdInicial;

        private readonly TextBox _txtCodigo;
        private readonly TextBox _txtCodigoBarra;
        private readonly TextBox _txtNombre;
        private readonly TextBox _txtDescripcion;
        private readonly NumericUpDown _numPrecio;
        private readonly ComboBox _cboCategoria;
        private readonly ComboBox _cboTasaIsv;
        private readonly NumericUpDown _numStockMinimo;
        private readonly CheckBox _chkActivo;
        private readonly Label _lblErrorGeneral;
        private readonly Button _btnGuardarGeneral;

        private readonly TabPage _tabRepuesto;
        private readonly TextBox _txtNumeroParte;
        private readonly TextBox _txtMarcaFabricante;
        private readonly CheckBox _chkEsOriginal;
        private readonly Label _lblErrorRepuesto;

        private readonly TabPage _tabVehiculos;
        private readonly DataGridView _gridVehiculos;
        private readonly TextBox _txtMarcaVehiculo;
        private readonly TextBox _txtModeloVehiculo;
        private readonly NumericUpDown _numAnioDesde;
        private readonly NumericUpDown _numAnioHasta;
        private readonly Label _lblErrorVehiculo;

        private readonly TabPage _tabEquivalencias;
        private readonly DataGridView _gridEquivalencias;
        private readonly TextBox _txtNumeroOem;
        private readonly TextBox _txtFabricanteOem;
        private readonly Label _lblErrorEquivalencia;

        private readonly TabPage _tabPrecios;
        private readonly DataGridView _gridPrecios;
        private readonly ComboBox _cboProveedor;
        private readonly NumericUpDown _numPrecioProveedor;
        private readonly Label _lblErrorPrecio;

        public FormProducto(ProductoDto? productoExistente)
        {
            _productoId = productoExistente?.Id;
            _categoriaIdInicial = productoExistente?.CategoriaId;

            Text = productoExistente == null ? Textos.Inventario.ProductoTituloNuevo : string.Format(Textos.Inventario.ProductoTituloEditarFormato, productoExistente.Codigo);
            ClientSize = new Size(640, 540);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(600, 480);

            var tabs = new TabControl { Dock = DockStyle.Fill };

            // ============ Pestaña General ============
            var tabGeneral = new TabPage(Textos.Inventario.TabGeneral);

            var lblCodigo = new Label { Text = Textos.Inventario.CampoCodigo, AutoSize = true, Location = new Point(20, 16) };
            _txtCodigo = new TextBox { Location = new Point(20, 36), Size = new Size(180, 26), Enabled = productoExistente == null };

            var lblNombre = new Label { Text = Textos.Inventario.CampoNombre, AutoSize = true, Location = new Point(220, 16) };
            _txtNombre = new TextBox { Location = new Point(220, 36), Size = new Size(380, 26) };

            var lblDescripcion = new Label { Text = Textos.Inventario.CampoDescripcion, AutoSize = true, Location = new Point(20, 74) };
            _txtDescripcion = new TextBox { Location = new Point(20, 94), Size = new Size(580, 50), Multiline = true };

            // Fila nueva de código de barras, debajo de la descripción — el
            // resto de las filas (precio en adelante) se corrió 40px hacia
            // abajo para hacerle espacio, con margen extra al final para no
            // repetir los bugs de layout de revisiones anteriores.
            var lblCodigoBarra = new Label { Text = Textos.Inventario.CampoCodigoBarra, AutoSize = true, Location = new Point(20, 156) };
            _txtCodigoBarra = new TextBox { Location = new Point(20, 176), Size = new Size(220, 26) };

            var lblPrecio = new Label { Text = Textos.Inventario.CampoPrecioUnitario, AutoSize = true, Location = new Point(20, 216) };
            _numPrecio = new NumericUpDown { Location = new Point(20, 236), Size = new Size(140, 26), DecimalPlaces = 2, Maximum = 999999, ThousandsSeparator = true };

            var lblCategoria = new Label { Text = Textos.Inventario.CampoCategoria, AutoSize = true, Location = new Point(180, 216) };
            _cboCategoria = new ComboBox
            {
                Location = new Point(180, 236), Size = new Size(300, 26), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(CategoriaDto.Nombre), ValueMember = nameof(CategoriaDto.Id)
            };
            var btnNuevaCategoria = new Button { Text = "+", Location = new Point(486, 235), Size = new Size(30, 26) };
            btnNuevaCategoria.Click += BtnNuevaCategoria_Click;

            var lblTasaIsv = new Label { Text = Textos.Inventario.CampoTasaIsv, AutoSize = true, Location = new Point(20, 276) };
            _cboTasaIsv = new ComboBox { Location = new Point(20, 296), Size = new Size(100, 26), DropDownStyle = ComboBoxStyle.DropDownList };
            _cboTasaIsv.Items.AddRange(new object[] { "0", "15", "18" });
            _cboTasaIsv.SelectedItem = "15";

            var lblStockMinimo = new Label { Text = Textos.Inventario.CampoStockMinimo, AutoSize = true, Location = new Point(140, 276) };
            _numStockMinimo = new NumericUpDown { Location = new Point(140, 296), Size = new Size(100, 26), Maximum = 100000 };

            _chkActivo = new CheckBox { Text = Textos.Comun.CampoActivo, AutoSize = true, Location = new Point(260, 300), Checked = true, Visible = productoExistente != null };

            _lblErrorGeneral = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(580, 32), Location = new Point(20, 334) };

            _btnGuardarGeneral = new Button
            {
                Text = productoExistente == null ? Textos.Inventario.BotonCrearProducto : Textos.Inventario.BotonGuardarCambios,
                Location = new Point(20, 370), Size = new Size(180, 32),
                BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat
            };
            _btnGuardarGeneral.FlatAppearance.BorderSize = 0;
            _btnGuardarGeneral.Click += BtnGuardarGeneral_Click;

            tabGeneral.Controls.AddRange(new Control[]
            {
                lblCodigo, _txtCodigo, lblNombre, _txtNombre, lblDescripcion, _txtDescripcion,
                lblCodigoBarra, _txtCodigoBarra,
                lblPrecio, _numPrecio, lblCategoria, _cboCategoria, btnNuevaCategoria,
                lblTasaIsv, _cboTasaIsv, lblStockMinimo, _numStockMinimo, _chkActivo,
                _lblErrorGeneral, _btnGuardarGeneral
            });

            // ============ Pestaña Repuesto ============
            _tabRepuesto = new TabPage(Textos.Inventario.TabRepuesto) { Enabled = _productoId.HasValue };

            var lblNumeroParte = new Label { Text = Textos.Inventario.CampoNumeroParte, AutoSize = true, Location = new Point(20, 20) };
            _txtNumeroParte = new TextBox { Location = new Point(20, 40), Size = new Size(240, 26) };

            var lblMarcaFabricante = new Label { Text = Textos.Inventario.CampoMarcaFabricante, AutoSize = true, Location = new Point(280, 20) };
            _txtMarcaFabricante = new TextBox { Location = new Point(280, 40), Size = new Size(240, 26) };

            _chkEsOriginal = new CheckBox { Text = Textos.Inventario.CampoEsOriginal, AutoSize = true, Location = new Point(20, 78), Checked = true };

            _lblErrorRepuesto = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(500, 32), Location = new Point(20, 108) };

            var btnGuardarRepuesto = new Button
            {
                Text = Textos.Comun.BotonGuardar, Location = new Point(20, 144), Size = new Size(140, 32),
                BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat
            };
            btnGuardarRepuesto.FlatAppearance.BorderSize = 0;
            btnGuardarRepuesto.Click += BtnGuardarRepuesto_Click;

            _tabRepuesto.Controls.AddRange(new Control[]
            {
                lblNumeroParte, _txtNumeroParte, lblMarcaFabricante, _txtMarcaFabricante,
                _chkEsOriginal, _lblErrorRepuesto, btnGuardarRepuesto
            });

            // ============ Pestaña Vehículos compatibles ============
            _tabVehiculos = new TabPage(Textos.Inventario.TabVehiculos) { Enabled = _productoId.HasValue };

            var pnlVehiculosInputs = new Panel { Dock = DockStyle.Top, Height = 108, BackColor = Color.White };
            var lblMarcaVeh = new Label { Text = Textos.Inventario.CampoMarca, AutoSize = true, Location = new Point(20, 10) };
            _txtMarcaVehiculo = new TextBox { Location = new Point(20, 30), Size = new Size(140, 26) };
            var lblModeloVeh = new Label { Text = Textos.Inventario.CampoModelo, AutoSize = true, Location = new Point(170, 10) };
            _txtModeloVehiculo = new TextBox { Location = new Point(170, 30), Size = new Size(140, 26) };
            var lblAnioDesde = new Label { Text = Textos.Inventario.CampoAnioDesde, AutoSize = true, Location = new Point(320, 10) };
            _numAnioDesde = new NumericUpDown { Location = new Point(320, 30), Size = new Size(80, 26), Minimum = 1950, Maximum = 2100, Value = 2000 };
            var lblAnioHasta = new Label { Text = Textos.Inventario.CampoAnioHasta, AutoSize = true, Location = new Point(410, 10) };
            _numAnioHasta = new NumericUpDown { Location = new Point(410, 30), Size = new Size(80, 26), Minimum = 1950, Maximum = 2100, Value = 2000 };
            var btnAgregarVehiculo = new Button { Text = Textos.Comun.BotonAgregar, Location = new Point(500, 29), Size = new Size(100, 28) };
            btnAgregarVehiculo.Click += BtnAgregarVehiculo_Click;
            _lblErrorVehiculo = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(580, 40), Location = new Point(20, 62) };
            pnlVehiculosInputs.Controls.AddRange(new Control[]
            {
                lblMarcaVeh, _txtMarcaVehiculo, lblModeloVeh, _txtModeloVehiculo,
                lblAnioDesde, _numAnioDesde, lblAnioHasta, _numAnioHasta, btnAgregarVehiculo, _lblErrorVehiculo
            });

            _gridVehiculos = new DataGridView();
            GridStyler.Aplicar(_gridVehiculos);
            _gridVehiculos.Columns.Add("Marca", "Marca");
            _gridVehiculos.Columns.Add("Modelo", "Modelo");
            _gridVehiculos.Columns.Add("AnioDesde", "Año desde");
            _gridVehiculos.Columns.Add("AnioHasta", "Año hasta");

            _tabVehiculos.Controls.Add(_gridVehiculos);
            _tabVehiculos.Controls.Add(pnlVehiculosInputs);

            // ============ Pestaña Equivalencias OEM ============
            _tabEquivalencias = new TabPage(Textos.Inventario.TabEquivalencias) { Enabled = _productoId.HasValue };

            // Height = 98: _lblErrorEquivalencia (y62-92) necesita 92px de
            // alto, más margen — con 90 quedaba cortada por 2px.
            var pnlEquivInputs = new Panel { Dock = DockStyle.Top, Height = 98, BackColor = Color.White };
            var lblNumeroOem = new Label { Text = Textos.Inventario.CampoNumeroOem, AutoSize = true, Location = new Point(20, 10) };
            _txtNumeroOem = new TextBox { Location = new Point(20, 30), Size = new Size(200, 26) };
            var lblFabricanteOem = new Label { Text = Textos.Inventario.CampoFabricante, AutoSize = true, Location = new Point(230, 10) };
            _txtFabricanteOem = new TextBox { Location = new Point(230, 30), Size = new Size(200, 26) };
            var btnAgregarEquivalente = new Button { Text = Textos.Comun.BotonAgregar, Location = new Point(440, 29), Size = new Size(100, 28) };
            btnAgregarEquivalente.Click += BtnAgregarEquivalente_Click;
            _lblErrorEquivalencia = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(580, 30), Location = new Point(20, 62) };
            pnlEquivInputs.Controls.AddRange(new Control[]
            {
                lblNumeroOem, _txtNumeroOem, lblFabricanteOem, _txtFabricanteOem, btnAgregarEquivalente, _lblErrorEquivalencia
            });

            _gridEquivalencias = new DataGridView();
            GridStyler.Aplicar(_gridEquivalencias);
            _gridEquivalencias.Columns.Add("NumeroOEM", "Número OEM");
            _gridEquivalencias.Columns.Add("Fabricante", "Fabricante");

            _tabEquivalencias.Controls.Add(_gridEquivalencias);
            _tabEquivalencias.Controls.Add(pnlEquivInputs);

            // ============ Pestaña Proveedores y precios ============
            _tabPrecios = new TabPage(Textos.Inventario.TabPrecios) { Enabled = _productoId.HasValue };

            // Height = 98: _lblErrorPrecio (y62-92) necesita 92px de alto,
            // más margen — con 90 quedaba cortada por 2px.
            var pnlPreciosInputs = new Panel { Dock = DockStyle.Top, Height = 98, BackColor = Color.White };
            var lblProveedor = new Label { Text = Textos.Comun.CampoProveedor, AutoSize = true, Location = new Point(20, 10) };
            _cboProveedor = new ComboBox
            {
                Location = new Point(20, 30), Size = new Size(260, 26), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(TerceroDto.Nombre), ValueMember = nameof(TerceroDto.Id)
            };
            var lblPrecioProveedor = new Label { Text = Textos.Inventario.CampoPrecioCompra, AutoSize = true, Location = new Point(290, 10) };
            _numPrecioProveedor = new NumericUpDown { Location = new Point(290, 30), Size = new Size(140, 26), DecimalPlaces = 2, Maximum = 999999 };
            var btnGuardarPrecio = new Button { Text = Textos.Comun.BotonGuardar, Location = new Point(440, 29), Size = new Size(100, 28) };
            btnGuardarPrecio.Click += BtnGuardarPrecio_Click;
            _lblErrorPrecio = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(580, 30), Location = new Point(20, 62) };
            pnlPreciosInputs.Controls.AddRange(new Control[]
            {
                lblProveedor, _cboProveedor, lblPrecioProveedor, _numPrecioProveedor, btnGuardarPrecio, _lblErrorPrecio
            });

            _gridPrecios = new DataGridView();
            GridStyler.Aplicar(_gridPrecios);
            _gridPrecios.Columns.Add("Nombre", "Proveedor");
            _gridPrecios.Columns.Add("Telefono", "Teléfono");
            _gridPrecios.Columns.Add("PrecioCompra", "Precio de compra");

            _tabPrecios.Controls.Add(_gridPrecios);
            _tabPrecios.Controls.Add(pnlPreciosInputs);

            tabs.TabPages.AddRange(new[] { tabGeneral, _tabRepuesto, _tabVehiculos, _tabEquivalencias, _tabPrecios });

            var pnlBotones = new Panel { Dock = DockStyle.Bottom, Height = 48, BackColor = Color.White };
            var btnCerrar = new Button { Text = Textos.Inventario.BotonCerrar, Location = new Point(12, 8), Size = new Size(100, 32) };
            btnCerrar.Click += (s, e) => { DialogResult = DialogResult.OK; Close(); };
            pnlBotones.Controls.Add(btnCerrar);

            Controls.Add(tabs);
            Controls.Add(pnlBotones);

            if (productoExistente != null)
            {
                _txtCodigo.Text = productoExistente.Codigo;
                _txtCodigoBarra.Text = productoExistente.CodigoBarra;
                _txtNombre.Text = productoExistente.Nombre;
                _txtDescripcion.Text = productoExistente.Descripcion;
                _numPrecio.Value = productoExistente.PrecioUnitario;
                _cboTasaIsv.SelectedItem = ((int)productoExistente.TasaISV).ToString();
                _numStockMinimo.Value = productoExistente.StockMinimo;
                _chkActivo.Checked = productoExistente.Activo;
            }

            Load += FormProducto_Load;
        }

        private async void FormProducto_Load(object? sender, EventArgs e)
        {
            try
            {
                var categorias = await CategoryService.ListarAsync();
                _cboCategoria.DataSource = categorias;
                if (_categoriaIdInicial.HasValue)
                    _cboCategoria.SelectedValue = _categoriaIdInicial.Value;
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Inventario.NoSeCargaronCategoriasPrefijo + ex.Message);
            }

            if (_productoId.HasValue)
                await CargarDetalleRepuestoAsync();
        }

        private async System.Threading.Tasks.Task CargarDetalleRepuestoAsync()
        {
            try
            {
                var detalle = await RepuestoDetalleService.ObtenerAsync(_productoId!.Value);

                _txtNumeroParte.Text = detalle.NumeroParte;
                _txtMarcaFabricante.Text = detalle.MarcaFabricante;
                _chkEsOriginal.Checked = detalle.EsOriginal ?? true;

                _gridVehiculos.Rows.Clear();
                foreach (var v in detalle.Vehiculos)
                    _gridVehiculos.Rows.Add(v.Marca, v.Modelo, v.AnioDesde, v.AnioHasta);

                _gridEquivalencias.Rows.Clear();
                foreach (var eq in detalle.Equivalentes)
                    _gridEquivalencias.Rows.Add(eq.NumeroOEM, eq.Fabricante);

                var proveedores = await TerceroService.ListarProveedoresAsync(true, null, 1, 500);
                _cboProveedor.DataSource = proveedores.Terceros;

                var precios = await TerceroService.CompararPreciosAsync(_productoId.Value);
                _gridPrecios.Rows.Clear();
                foreach (var pr in precios)
                    _gridPrecios.Rows.Add(pr.Nombre, pr.Telefono, pr.PrecioCompra);
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Inventario.NoSeCargoDetalleRepuestoPrefijo + ex.Message);
            }
        }

        private async void BtnNuevaCategoria_Click(object? sender, EventArgs e)
        {
            using var form = new FormCategoriaRapida();
            if (form.ShowDialog(this) == DialogResult.OK && form.CategoriaIdCreada.HasValue)
            {
                var categorias = await CategoryService.ListarAsync();
                _cboCategoria.DataSource = categorias;
                _cboCategoria.SelectedValue = form.CategoriaIdCreada.Value;
            }
        }

        private async void BtnGuardarGeneral_Click(object? sender, EventArgs e)
        {
            var codigo = _txtCodigo.Text.Trim();
            var nombre = _txtNombre.Text.Trim();

            if (codigo.Length == 0)
            {
                _lblErrorGeneral.Text = Textos.Inventario.ErrorCodigoRequerido;
                return;
            }
            if (nombre.Length == 0)
            {
                _lblErrorGeneral.Text = Textos.Inventario.ErrorNombreRequerido;
                return;
            }

            int? categoriaId = _cboCategoria.SelectedValue as int?;
            decimal tasaIsv = decimal.Parse((string)_cboTasaIsv.SelectedItem!);
            var usuarioId = SessionContext.Current?.UsuarioId;
            var codigoBarra = string.IsNullOrWhiteSpace(_txtCodigoBarra.Text) ? null : _txtCodigoBarra.Text.Trim();

            _btnGuardarGeneral.Enabled = false;
            try
            {
                if (_productoId == null)
                {
                    var (exito, mensaje, id) = await ProductService.CrearAsync(
                        codigo, nombre, _txtDescripcion.Text.Trim(), _numPrecio.Value,
                        categoriaId, tasaIsv, (int)_numStockMinimo.Value, usuarioId, codigoBarra);

                    if (exito)
                    {
                        _productoId = id;
                        _txtCodigo.Enabled = false; // sp_ActualizarProducto nunca toca Codigo: ya no se puede editar tras crear.
                        _tabRepuesto.Enabled = true;
                        _tabVehiculos.Enabled = true;
                        _tabEquivalencias.Enabled = true;
                        _tabPrecios.Enabled = true;
                        _chkActivo.Visible = true;
                        _btnGuardarGeneral.Text = Textos.Inventario.BotonGuardarCambios;
                        Text = string.Format(Textos.Inventario.ProductoTituloEditarFormato, codigo);
                        MostrarInfo(mensaje);
                        await CargarDetalleRepuestoAsync();
                    }
                    else
                    {
                        _lblErrorGeneral.Text = mensaje;
                    }
                }
                else
                {
                    var (exito, mensaje) = await ProductService.ActualizarAsync(
                        _productoId.Value, nombre, _txtDescripcion.Text.Trim(), _numPrecio.Value,
                        categoriaId, tasaIsv, (int)_numStockMinimo.Value, _chkActivo.Checked, usuarioId, codigoBarra);

                    _lblErrorGeneral.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                    _lblErrorGeneral.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoGuardarPrefijo + ex.Message);
            }
            finally
            {
                _btnGuardarGeneral.Enabled = true;
            }
        }

        private async void BtnGuardarRepuesto_Click(object? sender, EventArgs e)
        {
            if (_productoId == null) return;

            try
            {
                var (exito, mensaje) = await RepuestoDetalleService.GuardarDetalleAsync(
                    _productoId.Value,
                    string.IsNullOrWhiteSpace(_txtNumeroParte.Text) ? null : _txtNumeroParte.Text.Trim(),
                    string.IsNullOrWhiteSpace(_txtMarcaFabricante.Text) ? null : _txtMarcaFabricante.Text.Trim(),
                    _chkEsOriginal.Checked,
                    SessionContext.Current?.UsuarioId);

                _lblErrorRepuesto.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblErrorRepuesto.Text = mensaje;
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoGuardarPrefijo + ex.Message);
            }
        }

        private async void BtnAgregarVehiculo_Click(object? sender, EventArgs e)
        {
            if (_productoId == null) return;

            var marca = _txtMarcaVehiculo.Text.Trim();
            var modelo = _txtModeloVehiculo.Text.Trim();
            if (marca.Length == 0 || modelo.Length == 0)
            {
                _lblErrorVehiculo.Text = Textos.Inventario.ErrorMarcaModeloRequeridos;
                return;
            }

            try
            {
                var (exito, mensaje, _) = await RepuestoDetalleService.AgregarVehiculoAsync(
                    _productoId.Value, marca, modelo, (int)_numAnioDesde.Value, (int)_numAnioHasta.Value,
                    SessionContext.Current?.UsuarioId);

                if (exito)
                {
                    _gridVehiculos.Rows.Add(marca, modelo, (int)_numAnioDesde.Value, (int)_numAnioHasta.Value);
                    _txtMarcaVehiculo.Clear();
                    _txtModeloVehiculo.Clear();
                    _lblErrorVehiculo.Text = string.Empty;
                }
                else
                {
                    _lblErrorVehiculo.ForeColor = UiTheme.Error;
                    _lblErrorVehiculo.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoAgregarPrefijo + ex.Message);
            }
        }

        private async void BtnAgregarEquivalente_Click(object? sender, EventArgs e)
        {
            if (_productoId == null) return;

            var numero = _txtNumeroOem.Text.Trim();
            if (numero.Length == 0)
            {
                _lblErrorEquivalencia.Text = Textos.Inventario.ErrorNumeroOemRequerido;
                return;
            }

            try
            {
                var fabricante = string.IsNullOrWhiteSpace(_txtFabricanteOem.Text) ? null : _txtFabricanteOem.Text.Trim();
                var (exito, mensaje, _) = await RepuestoDetalleService.AgregarEquivalenteAsync(
                    _productoId.Value, numero, fabricante, SessionContext.Current?.UsuarioId);

                if (exito)
                {
                    _gridEquivalencias.Rows.Add(numero, fabricante);
                    _txtNumeroOem.Clear();
                    _txtFabricanteOem.Clear();
                    _lblErrorEquivalencia.Text = string.Empty;
                }
                else
                {
                    _lblErrorEquivalencia.ForeColor = UiTheme.Error;
                    _lblErrorEquivalencia.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoAgregarPrefijo + ex.Message);
            }
        }

        private async void BtnGuardarPrecio_Click(object? sender, EventArgs e)
        {
            if (_productoId == null || _cboProveedor.SelectedValue is not int proveedorId)
            {
                _lblErrorPrecio.Text = Textos.Inventario.ErrorSeleccioneProveedor;
                return;
            }

            try
            {
                var (exito, mensaje) = await TerceroService.GuardarPrecioAsync(
                    _productoId.Value, proveedorId, _numPrecioProveedor.Value, SessionContext.Current?.UsuarioId);

                _lblErrorPrecio.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblErrorPrecio.Text = mensaje;

                if (exito)
                {
                    var precios = await TerceroService.CompararPreciosAsync(_productoId.Value);
                    _gridPrecios.Rows.Clear();
                    foreach (var pr in precios)
                        _gridPrecios.Rows.Add(pr.Nombre, pr.Telefono, pr.PrecioCompra);
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Inventario.NoSeGuardoPrecioPrefijo + ex.Message);
            }
        }
    }
}
