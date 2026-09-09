using System;
using System.Drawing;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Inventario
{
    // Ficha de producto sin pestañas ni ventana propia (inspirada en la
    // ficha de producto de Odoo, simplificada): reemplaza al grid de
    // tarjetas en el mismo lugar dentro de InventarioControl, en vez de
    // abrir un diálogo aparte. Arranca en modo vista para un producto
    // existente, o directo en modo edición para uno nuevo.
    public sealed class ProductDetailControl : UserControl
    {
        private int? _productoId;
        private ProductoDto? _productoActual;

        // ---- Encabezado ----
        private readonly LinkLabel _lnkVolver;
        private readonly Label _lblNombreVista;
        private readonly Label _lblCampoNombre;
        private readonly TextBox _txtNombre;
        private readonly Label _lblCodigoVista;
        private readonly Label _lblCampoCodigo;
        private readonly TextBox _txtCodigo;
        private readonly Button _btnEditar;
        private readonly Button _btnAgregarAPack;
        private readonly Button _btnGuardar;
        private readonly Button _btnCancelar;

        // ---- Sección General ----
        private readonly TextBox _txtDescripcion;
        private readonly NumericUpDown _numPrecio;
        private readonly ComboBox _cboCategoria;
        private readonly ComboBox _cboTasaIsv;
        private readonly ComboBox _cboUnidadMedida;
        private readonly NumericUpDown _numStockMinimo;
        private readonly Label _lblStockActualValor;
        private readonly CheckBox _chkActivo;
        private readonly Label _lblErrorGeneral;

        // ---- Sección Repuesto ----
        private readonly Panel _pnlRepuesto;
        private readonly TextBox _txtNumeroParte;
        private readonly TextBox _txtMarcaFabricante;
        private readonly CheckBox _chkEsOriginal;
        private readonly Label _lblErrorRepuesto;

        // ---- Sección Vehículos ----
        private readonly Panel _pnlVehiculos;
        private readonly DataGridView _gridVehiculos;
        private readonly TextBox _txtMarcaVehiculo;
        private readonly TextBox _txtModeloVehiculo;
        private readonly NumericUpDown _numAnioDesde;
        private readonly NumericUpDown _numAnioHasta;
        private readonly Label _lblErrorVehiculo;

        // ---- Sección Equivalencias ----
        private readonly Panel _pnlEquivalencias;
        private readonly DataGridView _gridEquivalencias;
        private readonly TextBox _txtNumeroOem;
        private readonly TextBox _txtFabricanteOem;
        private readonly Label _lblErrorEquivalencia;

        // ---- Sección Proveedores ----
        private readonly Panel _pnlPrecios;
        private readonly DataGridView _gridPrecios;
        private readonly ComboBox _cboProveedor;
        private readonly NumericUpDown _numPrecioProveedor;
        private readonly Label _lblErrorPrecio;

        public event EventHandler? Volver;
        public event EventHandler<ProductoDto>? Guardado;

        public ProductDetailControl(ProductoDto? productoExistente)
        {
            _productoId = productoExistente?.Id;
            _productoActual = productoExistente;

            Dock = DockStyle.Fill;
            AutoScroll = true;
            // Blanco, no el gris de fondo de la lista: así el detalle se ve
            // como una sola página continua en vez de un recuadro chico
            // flotando sobre un área vacía.
            BackColor = Color.White;

            // ============ Encabezado ============
            var pnlEncabezado = new Panel { Dock = DockStyle.Top, Height = 92, BackColor = Color.White };

            _lnkVolver = new LinkLabel { Text = Textos.Inventario.EnlaceVolver, AutoSize = true, Location = new Point(32, 6) };
            _lnkVolver.Click += (s, e) => Volver?.Invoke(this, EventArgs.Empty);

            _lblNombreVista = new Label
            {
                Text = productoExistente?.Nombre ?? string.Empty,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Location = new Point(32, 44),
                Visible = productoExistente != null
            };

            _lblCampoNombre = new Label { Text = Textos.Inventario.CampoNombre, AutoSize = true, Location = new Point(32, 30), Visible = productoExistente == null };
            _txtNombre = new TextBox
            {
                Text = productoExistente?.Nombre ?? string.Empty,
                Font = UiTheme.FuenteTitulo,
                Location = new Point(32, 48),
                Size = new Size(400, 32),
                Visible = productoExistente == null
            };

            _lblCodigoVista = new Label { Text = productoExistente?.Codigo ?? string.Empty, ForeColor = UiTheme.TextoTenue, AutoSize = true, Location = new Point(456, 54), Visible = productoExistente != null };

            _lblCampoCodigo = new Label { Text = Textos.Inventario.CampoCodigo, AutoSize = true, Location = new Point(456, 30), Visible = productoExistente == null };
            _txtCodigo = new TextBox { Text = productoExistente?.Codigo ?? string.Empty, Location = new Point(456, 48), Size = new Size(180, 26), Visible = productoExistente == null };

            var pnlBotones = new FlowLayoutPanel
            {
                Dock = DockStyle.Right,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                Padding = new Padding(0, 30, 16, 0)
            };

            _btnCancelar = new Button { Text = Textos.Comun.BotonCancelar, AutoSize = true, Padding = new Padding(14, 0, 14, 0), Height = 32, Margin = new Padding(8, 0, 0, 0) };
            _btnCancelar.Click += (s, e) => Cancelar();

            _btnGuardar = new Button
            {
                Text = Textos.Comun.BotonGuardar, AutoSize = true, Padding = new Padding(14, 0, 14, 0), Height = 32,
                BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Margin = new Padding(8, 0, 0, 0)
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += async (s, e) => await GuardarGeneralAsync();

            _btnAgregarAPack = new Button { Text = Textos.Inventario.BotonAgregarAPack, AutoSize = true, Padding = new Padding(14, 0, 14, 0), Height = 32, Margin = new Padding(8, 0, 0, 0) };
            _btnAgregarAPack.Click += BtnAgregarAPack_Click;

            _btnEditar = new Button
            {
                Text = Textos.Comun.BotonEditar, AutoSize = true, Padding = new Padding(14, 0, 14, 0), Height = 32,
                BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Margin = new Padding(8, 0, 0, 0)
            };
            _btnEditar.FlatAppearance.BorderSize = 0;
            _btnEditar.Click += (s, e) => EntrarModoEdicion();

            // Orden de agregado = orden visual izquierda→derecha dentro del panel.
            pnlBotones.Controls.AddRange(new Control[] { _btnEditar, _btnAgregarAPack, _btnGuardar, _btnCancelar });

            pnlEncabezado.Controls.AddRange(new Control[] { _lnkVolver, _lblNombreVista, _lblCampoNombre, _txtNombre, _lblCodigoVista, _lblCampoCodigo, _txtCodigo });
            pnlEncabezado.Controls.Add(pnlBotones);

            // ============ Sección General ============
            // Filas espaciadas ~90px y campos más anchos a propósito: con
            // toda la pantalla disponible (ya no es un diálogo de 640px), un
            // formulario denso como el de antes se ve amontonado en una
            // esquina — más aire entre filas y columnas es lo que hace que
            // se sienta ordenado, no solo que no se solape.
            var pnlGeneral = new Panel { Dock = DockStyle.Top, Height = 380, BackColor = Color.White, Padding = new Padding(0, 1, 0, 0) };

            var lblDescripcion = new Label { Text = Textos.Inventario.CampoDescripcion, AutoSize = true, Location = new Point(32, 20) };
            _txtDescripcion = new TextBox { Text = productoExistente?.Descripcion, Location = new Point(32, 40), Size = new Size(760, 60), Multiline = true };

            var lblPrecio = new Label { Text = Textos.Inventario.CampoPrecioUnitario, AutoSize = true, Location = new Point(32, 128) };
            _numPrecio = new NumericUpDown { Location = new Point(32, 148), Size = new Size(180, 28), DecimalPlaces = 2, Maximum = 999999, ThousandsSeparator = true, Value = productoExistente?.PrecioUnitario ?? 0 };

            var lblCategoria = new Label { Text = Textos.Inventario.CampoCategoria, AutoSize = true, Location = new Point(250, 128) };
            _cboCategoria = new ComboBox
            {
                Location = new Point(250, 148), Size = new Size(320, 28), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(CategoriaDto.Nombre), ValueMember = nameof(CategoriaDto.Id)
            };
            var btnNuevaCategoria = new Button { Text = "+", Location = new Point(586, 147), Size = new Size(32, 28) };
            btnNuevaCategoria.Click += BtnNuevaCategoria_Click;

            var lblStockActual = new Label { Text = Textos.Inventario.CampoStockActual, AutoSize = true, Location = new Point(660, 128) };
            _lblStockActualValor = new Label { Text = "—", AutoSize = true, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Location = new Point(660, 150) };

            var lblTasaIsv = new Label { Text = Textos.Inventario.CampoTasaIsv, AutoSize = true, Location = new Point(32, 214) };
            _cboTasaIsv = new ComboBox { Location = new Point(32, 234), Size = new Size(140, 28), DropDownStyle = ComboBoxStyle.DropDownList };
            _cboTasaIsv.Items.AddRange(new object[] { "0", "15", "18" });
            _cboTasaIsv.SelectedItem = productoExistente != null ? ((int)productoExistente.TasaISV).ToString() : "15";

            var lblUnidadMedida = new Label { Text = Textos.Inventario.CampoUnidadMedida, AutoSize = true, Location = new Point(210, 214) };
            _cboUnidadMedida = new ComboBox
            {
                Location = new Point(210, 234), Size = new Size(220, 28), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(UnidadMedidaDto.Nombre), ValueMember = nameof(UnidadMedidaDto.Id)
            };
            _cboUnidadMedida.SelectedIndexChanged += (s, e) =>
            {
                if (_cboUnidadMedida.SelectedItem is UnidadMedidaDto unidad)
                    CantidadFormatter.AplicarModoCantidad(_numStockMinimo, unidad.PermiteFraccion);
            };

            var lblStockMinimo = new Label { Text = Textos.Inventario.CampoStockMinimo, AutoSize = true, Location = new Point(470, 214) };
            _numStockMinimo = new NumericUpDown { Location = new Point(470, 234), Size = new Size(160, 28), Maximum = 100000, DecimalPlaces = 2, Increment = 0.01m, Value = productoExistente?.StockMinimo ?? 0 };

            _chkActivo = new CheckBox { Text = Textos.Comun.CampoActivo, AutoSize = true, Location = new Point(32, 296), Checked = productoExistente?.Activo ?? true, Visible = productoExistente != null };

            _lblErrorGeneral = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(700, 32), Location = new Point(32, 332) };

            pnlGeneral.Controls.AddRange(new Control[]
            {
                lblDescripcion, _txtDescripcion,
                lblPrecio, _numPrecio, lblCategoria, _cboCategoria, btnNuevaCategoria,
                lblStockActual, _lblStockActualValor,
                lblTasaIsv, _cboTasaIsv, lblStockMinimo, _numStockMinimo, lblUnidadMedida, _cboUnidadMedida,
                _chkActivo, _lblErrorGeneral
            });

            // ============ Secciones apiladas (solo con producto ya existente) ============
            _pnlRepuesto = ConstruirSeccionRepuesto(out _txtNumeroParte, out _txtMarcaFabricante, out _chkEsOriginal, out _lblErrorRepuesto);
            _pnlVehiculos = ConstruirSeccionVehiculos(out _gridVehiculos, out _txtMarcaVehiculo, out _txtModeloVehiculo, out _numAnioDesde, out _numAnioHasta, out _lblErrorVehiculo);
            _pnlEquivalencias = ConstruirSeccionEquivalencias(out _gridEquivalencias, out _txtNumeroOem, out _txtFabricanteOem, out _lblErrorEquivalencia);
            _pnlPrecios = ConstruirSeccionPrecios(out _gridPrecios, out _cboProveedor, out _numPrecioProveedor, out _lblErrorPrecio);

            var haySecciones = _productoId.HasValue;
            _pnlRepuesto.Visible = haySecciones;
            _pnlVehiculos.Visible = haySecciones;
            _pnlEquivalencias.Visible = haySecciones;
            _pnlPrecios.Visible = haySecciones;

            // Dock=Top apila en orden INVERSO al agregado (el último agregado
            // queda más arriba) — se agregan de abajo hacia arriba para que el
            // orden visual sea: encabezado, general, repuesto, vehículos,
            // equivalencias, precios.
            Controls.Add(_pnlPrecios);
            Controls.Add(_pnlEquivalencias);
            Controls.Add(_pnlVehiculos);
            Controls.Add(_pnlRepuesto);
            Controls.Add(pnlGeneral);
            Controls.Add(pnlEncabezado);

            AplicarModo(editando: productoExistente == null);

            Load += ProductDetailControl_Load;
        }

        private async void ProductDetailControl_Load(object? sender, EventArgs e)
        {
            try
            {
                var categorias = await CategoryService.ListarAsync();
                _cboCategoria.DataSource = categorias;
                if (_productoActual?.CategoriaId.HasValue == true)
                    _cboCategoria.SelectedValue = _productoActual.CategoriaId.Value;
            }
            catch (Exception ex)
            {
                _lblErrorGeneral.Text = Textos.Inventario.NoSeCargaronCategoriasPrefijo + ex.Message;
            }

            try
            {
                var unidades = await UnidadMedidaService.ObtenerActivasAsync();
                _cboUnidadMedida.DataSource = unidades;
                _cboUnidadMedida.SelectedValue = _productoActual?.UnidadMedidaId ?? 1;
            }
            catch (Exception ex)
            {
                _lblErrorGeneral.Text = Textos.Inventario.NoSeCargaronUnidadesPrefijo + ex.Message;
            }

            ActualizarStockActualVisible();

            if (_productoId.HasValue)
                await CargarDetalleRepuestoAsync();
        }

        private void ActualizarStockActualVisible()
        {
            _lblStockActualValor.Text = _productoActual == null
                ? "—"
                : CantidadFormatter.FormatearCantidad(_productoActual.StockActual, _productoActual.PermiteFraccionUnidad) + " " + _productoActual.UnidadMedidaSimbolo;
        }

        // ============ Modo vista / edición (sección General) ============

        private void EntrarModoEdicion() => AplicarModo(editando: true);

        private void AplicarModo(bool editando)
        {
            _lblNombreVista.Visible = !editando;
            _lblCampoNombre.Visible = editando;
            _txtNombre.Visible = editando;
            // Código nunca se edita tras crear: una vez que el producto tiene
            // Id, el código se muestra siempre como etiqueta (aun editando),
            // nunca vuelve a ser el textbox — solo un producto nuevo (sin Id
            // todavía) lo tiene habilitado, y ese caso siempre está en modo
            // edición desde que se abre.
            _lblCodigoVista.Visible = _productoId.HasValue;
            _lblCampoCodigo.Visible = !_productoId.HasValue;
            _txtCodigo.Visible = !_productoId.HasValue;

            _btnEditar.Visible = !editando && _productoId.HasValue;
            _btnAgregarAPack.Visible = !editando && _productoId.HasValue;
            _btnGuardar.Visible = editando;
            _btnCancelar.Visible = editando;

            _txtDescripcion.ReadOnly = !editando;
            _numPrecio.Enabled = editando;
            _cboCategoria.Enabled = editando;
            _cboTasaIsv.Enabled = editando;
            _cboUnidadMedida.Enabled = editando;
            _numStockMinimo.Enabled = editando;
            _chkActivo.Enabled = editando;
        }

        private void Cancelar()
        {
            if (_productoActual == null)
            {
                Volver?.Invoke(this, EventArgs.Empty);
                return;
            }

            // Se descartan los cambios en memoria y se vuelve a modo vista con
            // los últimos datos guardados — sin volver a consultar la BD,
            // igual de simple que ya hacía FormProducto.
            _lblNombreVista.Text = _productoActual.Nombre;
            _txtNombre.Text = _productoActual.Nombre;
            _txtDescripcion.Text = _productoActual.Descripcion;
            _numPrecio.Value = _productoActual.PrecioUnitario;
            _cboTasaIsv.SelectedItem = ((int)_productoActual.TasaISV).ToString();
            _numStockMinimo.Value = _productoActual.StockMinimo;
            _chkActivo.Checked = _productoActual.Activo;
            if (_productoActual.CategoriaId.HasValue) _cboCategoria.SelectedValue = _productoActual.CategoriaId.Value;
            _cboUnidadMedida.SelectedValue = _productoActual.UnidadMedidaId;
            _lblErrorGeneral.Text = string.Empty;

            AplicarModo(editando: false);
        }

        private async Task GuardarGeneralAsync()
        {
            var nombre = _txtNombre.Text.Trim();
            var codigo = _txtCodigo.Text.Trim();

            if (!_productoId.HasValue && codigo.Length == 0)
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
            var tasaIsv = decimal.Parse((string)_cboTasaIsv.SelectedItem!);
            var unidadMedidaId = (int)(_cboUnidadMedida.SelectedValue ?? 1);
            var usuarioId = SessionContext.Current?.UsuarioId;

            _btnGuardar.Enabled = false;
            try
            {
                if (!_productoId.HasValue)
                {
                    var (exito, mensaje, id) = await ProductService.CrearAsync(
                        codigo, nombre, _txtDescripcion.Text.Trim(), _numPrecio.Value,
                        categoriaId, tasaIsv, _numStockMinimo.Value, unidadMedidaId, usuarioId);

                    if (!exito) { _lblErrorGeneral.Text = mensaje; return; }

                    _productoId = id;
                }
                else
                {
                    var (exito, mensaje) = await ProductService.ActualizarAsync(
                        _productoId.Value, nombre, _txtDescripcion.Text.Trim(), _numPrecio.Value,
                        categoriaId, tasaIsv, _numStockMinimo.Value, unidadMedidaId, _chkActivo.Checked, usuarioId);

                    if (!exito) { _lblErrorGeneral.Text = mensaje; return; }
                }

                _productoActual = new ProductoDto
                {
                    Id = _productoId!.Value,
                    // _txtCodigo ya trae el valor correcto en ambos casos: el
                    // recién tipeado al crear, o el original sin tocar al
                    // editar (el campo queda oculto y deshabilitado una vez
                    // que el producto existe).
                    Codigo = codigo,
                    Nombre = nombre,
                    Descripcion = _txtDescripcion.Text.Trim(),
                    PrecioUnitario = _numPrecio.Value,
                    CategoriaId = categoriaId,
                    NombreCategoria = (_cboCategoria.SelectedItem as CategoriaDto)?.Nombre,
                    TasaISV = tasaIsv,
                    StockActual = _productoActual?.StockActual ?? 0,
                    StockMinimo = _numStockMinimo.Value,
                    UnidadMedidaId = unidadMedidaId,
                    UnidadMedidaSimbolo = (_cboUnidadMedida.SelectedItem as UnidadMedidaDto)?.Simbolo,
                    PermiteFraccionUnidad = (_cboUnidadMedida.SelectedItem as UnidadMedidaDto)?.PermiteFraccion ?? true,
                    Activo = _chkActivo.Checked
                };

                _lblNombreVista.Text = _productoActual.Nombre;
                _lblCodigoVista.Text = _productoActual.Codigo;
                _lblErrorGeneral.Text = string.Empty;
                ActualizarStockActualVisible();

                _pnlRepuesto.Visible = true;
                _pnlVehiculos.Visible = true;
                _pnlEquivalencias.Visible = true;
                _pnlPrecios.Visible = true;
                await CargarDetalleRepuestoAsync();

                AplicarModo(editando: false);
                Guardado?.Invoke(this, _productoActual);
            }
            catch (Exception ex)
            {
                _lblErrorGeneral.Text = Textos.Comun.NoSePudoGuardarPrefijo + ex.Message;
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }

        private void BtnAgregarAPack_Click(object? sender, EventArgs e)
        {
            if (_productoActual == null) return;
            using var form = new FormArmarPaquete(_productoActual);
            form.ShowDialog(FindForm());
        }

        private async void BtnNuevaCategoria_Click(object? sender, EventArgs e)
        {
            using var form = new FormCategoriaRapida();
            if (form.ShowDialog(FindForm()) == DialogResult.OK && form.CategoriaIdCreada.HasValue)
            {
                var categorias = await CategoryService.ListarAsync();
                _cboCategoria.DataSource = categorias;
                _cboCategoria.SelectedValue = form.CategoriaIdCreada.Value;
            }
        }

        // ============ Sección Repuesto ============

        private Panel ConstruirSeccionRepuesto(out TextBox txtNumeroParte, out TextBox txtMarcaFabricante, out CheckBox chkEsOriginal, out Label lblError)
        {
            var panel = new Panel { Dock = DockStyle.Top, Height = 180, BackColor = Color.White, Margin = new Padding(0, 8, 0, 0) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionRepuesto, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), AutoSize = true, Location = new Point(20, 8) };

            var lblNumeroParte = new Label { Text = Textos.Inventario.CampoNumeroParte, AutoSize = true, Location = new Point(20, 36) };
            txtNumeroParte = new TextBox { Location = new Point(20, 56), Size = new Size(240, 26) };

            var lblMarcaFabricante = new Label { Text = Textos.Inventario.CampoMarcaFabricante, AutoSize = true, Location = new Point(280, 36) };
            txtMarcaFabricante = new TextBox { Location = new Point(280, 56), Size = new Size(240, 26) };

            chkEsOriginal = new CheckBox { Text = Textos.Inventario.CampoEsOriginal, AutoSize = true, Location = new Point(20, 94), Checked = true };

            lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(500, 32), Location = new Point(20, 124) };

            var btnGuardar = new Button { Text = Textos.Comun.BotonGuardar, Location = new Point(20, 158) };
            var txtNumeroParteRef = txtNumeroParte; var txtMarcaRef = txtMarcaFabricante; var chkOriginalRef = chkEsOriginal; var lblErrorRef = lblError;
            // El botón se reposiciona una vez conocido el ancho real de sus hermanos; se ancla arriba a la derecha visualmente vía Location fijo razonable.
            btnGuardar.Size = new Size(140, 32);
            btnGuardar.BackColor = UiTheme.Primario;
            btnGuardar.ForeColor = Color.White;
            btnGuardar.FlatStyle = FlatStyle.Flat;
            btnGuardar.FlatAppearance.BorderSize = 0;
            btnGuardar.Click += async (s, e) => await GuardarRepuestoAsync(txtNumeroParteRef, txtMarcaRef, chkOriginalRef, lblErrorRef);

            panel.Controls.AddRange(new Control[] { lblTitulo, lblNumeroParte, txtNumeroParte, lblMarcaFabricante, txtMarcaFabricante, chkEsOriginal, lblError, btnGuardar });
            return panel;
        }

        private async Task GuardarRepuestoAsync(TextBox txtNumeroParte, TextBox txtMarcaFabricante, CheckBox chkEsOriginal, Label lblError)
        {
            if (_productoId == null) return;
            try
            {
                var (exito, mensaje) = await RepuestoDetalleService.GuardarDetalleAsync(
                    _productoId.Value,
                    string.IsNullOrWhiteSpace(txtNumeroParte.Text) ? null : txtNumeroParte.Text.Trim(),
                    string.IsNullOrWhiteSpace(txtMarcaFabricante.Text) ? null : txtMarcaFabricante.Text.Trim(),
                    chkEsOriginal.Checked,
                    SessionContext.Current?.UsuarioId);

                lblError.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                lblError.Text = mensaje;
            }
            catch (Exception ex)
            {
                lblError.ForeColor = UiTheme.Error;
                lblError.Text = Textos.Comun.NoSePudoGuardarPrefijo + ex.Message;
            }
        }

        // ============ Sección Vehículos ============

        private Panel ConstruirSeccionVehiculos(out DataGridView grid, out TextBox txtMarca, out TextBox txtModelo, out NumericUpDown numAnioDesde, out NumericUpDown numAnioHasta, out Label lblError)
        {
            var panel = new Panel { Dock = DockStyle.Top, Height = 260, BackColor = Color.White, Margin = new Padding(0, 8, 0, 0) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionVehiculos, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), AutoSize = true, Location = new Point(20, 8) };

            var lblMarcaVeh = new Label { Text = Textos.Inventario.CampoMarca, AutoSize = true, Location = new Point(20, 36) };
            txtMarca = new TextBox { Location = new Point(20, 56), Size = new Size(140, 26) };
            var lblModeloVeh = new Label { Text = Textos.Inventario.CampoModelo, AutoSize = true, Location = new Point(170, 36) };
            txtModelo = new TextBox { Location = new Point(170, 56), Size = new Size(140, 26) };
            var lblAnioDesde = new Label { Text = Textos.Inventario.CampoAnioDesde, AutoSize = true, Location = new Point(320, 36) };
            numAnioDesde = new NumericUpDown { Location = new Point(320, 56), Size = new Size(80, 26), Minimum = 1950, Maximum = 2100, Value = 2000 };
            var lblAnioHasta = new Label { Text = Textos.Inventario.CampoAnioHasta, AutoSize = true, Location = new Point(410, 36) };
            numAnioHasta = new NumericUpDown { Location = new Point(410, 56), Size = new Size(80, 26), Minimum = 1950, Maximum = 2100, Value = 2000 };

            var gridLocal = new DataGridView();
            GridStyler.Aplicar(gridLocal);
            gridLocal.Location = new Point(20, 118);
            gridLocal.Size = new Size(600, 100);
            gridLocal.Dock = DockStyle.None;
            gridLocal.Columns.Add("Marca", "Marca");
            gridLocal.Columns.Add("Modelo", "Modelo");
            gridLocal.Columns.Add("AnioDesde", "Año desde");
            gridLocal.Columns.Add("AnioHasta", "Año hasta");
            grid = gridLocal;

            lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(500, 26), Location = new Point(500, 56) };

            var txtMarcaRef = txtMarca; var txtModeloRef = txtModelo; var numDesdeRef = numAnioDesde; var numHastaRef = numAnioHasta; var lblErrorRef = lblError; var gridRef = grid;
            var btnAgregar = new Button { Text = Textos.Comun.BotonAgregar, Location = new Point(500, 55), Size = new Size(90, 28) };
            btnAgregar.Click += async (s, e) => await AgregarVehiculoAsync(txtMarcaRef, txtModeloRef, numDesdeRef, numHastaRef, lblErrorRef, gridRef);

            panel.Controls.AddRange(new Control[] { lblTitulo, lblMarcaVeh, txtMarca, lblModeloVeh, txtModelo, lblAnioDesde, numAnioDesde, lblAnioHasta, numAnioHasta, btnAgregar, lblError, grid });
            return panel;
        }

        private async Task AgregarVehiculoAsync(TextBox txtMarca, TextBox txtModelo, NumericUpDown numAnioDesde, NumericUpDown numAnioHasta, Label lblError, DataGridView grid)
        {
            if (_productoId == null) return;

            var marca = txtMarca.Text.Trim();
            var modelo = txtModelo.Text.Trim();
            if (marca.Length == 0 || modelo.Length == 0)
            {
                lblError.Text = Textos.Inventario.ErrorMarcaModeloRequeridos;
                return;
            }

            try
            {
                var (exito, mensaje, _) = await RepuestoDetalleService.AgregarVehiculoAsync(
                    _productoId.Value, marca, modelo, (int)numAnioDesde.Value, (int)numAnioHasta.Value,
                    SessionContext.Current?.UsuarioId);

                if (exito)
                {
                    grid.Rows.Add(marca, modelo, (int)numAnioDesde.Value, (int)numAnioHasta.Value);
                    txtMarca.Clear();
                    txtModelo.Clear();
                    lblError.Text = string.Empty;
                }
                else
                {
                    lblError.ForeColor = UiTheme.Error;
                    lblError.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                lblError.ForeColor = UiTheme.Error;
                lblError.Text = Textos.Comun.NoSePudoAgregarPrefijo + ex.Message;
            }
        }

        // ============ Sección Equivalencias ============

        private Panel ConstruirSeccionEquivalencias(out DataGridView grid, out TextBox txtNumeroOem, out TextBox txtFabricante, out Label lblError)
        {
            var panel = new Panel { Dock = DockStyle.Top, Height = 220, BackColor = Color.White, Margin = new Padding(0, 8, 0, 0) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionEquivalencias, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), AutoSize = true, Location = new Point(20, 8) };

            var lblNumeroOem = new Label { Text = Textos.Inventario.CampoNumeroOem, AutoSize = true, Location = new Point(20, 36) };
            txtNumeroOem = new TextBox { Location = new Point(20, 56), Size = new Size(200, 26) };
            var lblFabricanteOem = new Label { Text = Textos.Inventario.CampoFabricante, AutoSize = true, Location = new Point(230, 36) };
            txtFabricante = new TextBox { Location = new Point(230, 56), Size = new Size(200, 26) };

            lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(400, 26), Location = new Point(500, 56) };

            var txtNumeroRef = txtNumeroOem; var txtFabRef = txtFabricante; var lblErrorRef = lblError;
            var gridLocal = new DataGridView();
            GridStyler.Aplicar(gridLocal);
            gridLocal.Location = new Point(20, 118);
            gridLocal.Size = new Size(600, 80);
            gridLocal.Dock = DockStyle.None;
            gridLocal.Columns.Add("NumeroOEM", "Número OEM");
            gridLocal.Columns.Add("Fabricante", "Fabricante");
            grid = gridLocal;
            var gridRef = grid;

            var btnAgregar = new Button { Text = Textos.Comun.BotonAgregar, Location = new Point(440, 55), Size = new Size(90, 28) };
            btnAgregar.Click += async (s, e) => await AgregarEquivalenteAsync(txtNumeroRef, txtFabRef, lblErrorRef, gridRef);

            panel.Controls.AddRange(new Control[] { lblTitulo, lblNumeroOem, txtNumeroOem, lblFabricanteOem, txtFabricante, btnAgregar, lblError, grid });
            return panel;
        }

        private async Task AgregarEquivalenteAsync(TextBox txtNumeroOem, TextBox txtFabricante, Label lblError, DataGridView grid)
        {
            if (_productoId == null) return;

            var numero = txtNumeroOem.Text.Trim();
            if (numero.Length == 0)
            {
                lblError.Text = Textos.Inventario.ErrorNumeroOemRequerido;
                return;
            }

            try
            {
                var fabricante = string.IsNullOrWhiteSpace(txtFabricante.Text) ? null : txtFabricante.Text.Trim();
                var (exito, mensaje, _) = await RepuestoDetalleService.AgregarEquivalenteAsync(
                    _productoId.Value, numero, fabricante, SessionContext.Current?.UsuarioId);

                if (exito)
                {
                    grid.Rows.Add(numero, fabricante);
                    txtNumeroOem.Clear();
                    txtFabricante.Clear();
                    lblError.Text = string.Empty;
                }
                else
                {
                    lblError.ForeColor = UiTheme.Error;
                    lblError.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                lblError.ForeColor = UiTheme.Error;
                lblError.Text = Textos.Comun.NoSePudoAgregarPrefijo + ex.Message;
            }
        }

        // ============ Sección Proveedores y precios ============

        private Panel ConstruirSeccionPrecios(out DataGridView grid, out ComboBox cboProveedor, out NumericUpDown numPrecio, out Label lblError)
        {
            var panel = new Panel { Dock = DockStyle.Top, Height = 220, BackColor = Color.White, Margin = new Padding(0, 8, 0, 0) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionPrecios, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), AutoSize = true, Location = new Point(20, 8) };

            var lblProveedor = new Label { Text = Textos.Comun.CampoProveedor, AutoSize = true, Location = new Point(20, 36) };
            cboProveedor = new ComboBox
            {
                Location = new Point(20, 56), Size = new Size(260, 26), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(ProveedorDto.Nombre), ValueMember = nameof(ProveedorDto.Id)
            };
            var lblPrecioProveedor = new Label { Text = Textos.Inventario.CampoPrecioCompra, AutoSize = true, Location = new Point(290, 36) };
            numPrecio = new NumericUpDown { Location = new Point(290, 56), Size = new Size(140, 26), DecimalPlaces = 2, Maximum = 999999 };

            lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(400, 26), Location = new Point(540, 56) };

            var cboProveedorRef = cboProveedor; var numPrecioRef = numPrecio; var lblErrorRef = lblError;
            var gridLocal = new DataGridView();
            GridStyler.Aplicar(gridLocal);
            gridLocal.Location = new Point(20, 118);
            gridLocal.Size = new Size(600, 80);
            gridLocal.Dock = DockStyle.None;
            gridLocal.Columns.Add("Nombre", "Proveedor");
            gridLocal.Columns.Add("Telefono", "Teléfono");
            gridLocal.Columns.Add("PrecioCompra", "Precio de compra");
            grid = gridLocal;
            var gridRef = grid;

            var btnGuardar = new Button { Text = Textos.Comun.BotonGuardar, Location = new Point(440, 55), Size = new Size(90, 28) };
            btnGuardar.Click += async (s, e) => await GuardarPrecioAsync(cboProveedorRef, numPrecioRef, lblErrorRef, gridRef);

            panel.Controls.AddRange(new Control[] { lblTitulo, lblProveedor, cboProveedor, lblPrecioProveedor, numPrecio, btnGuardar, lblError, grid });
            return panel;
        }

        private async Task GuardarPrecioAsync(ComboBox cboProveedor, NumericUpDown numPrecio, Label lblError, DataGridView grid)
        {
            if (_productoId == null || cboProveedor.SelectedValue is not int proveedorId)
            {
                lblError.Text = Textos.Inventario.ErrorSeleccioneProveedor;
                return;
            }

            try
            {
                var (exito, mensaje) = await ProveedorService.GuardarPrecioAsync(
                    _productoId.Value, proveedorId, numPrecio.Value, SessionContext.Current?.UsuarioId);

                lblError.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                lblError.Text = mensaje;

                if (exito)
                {
                    var precios = await ProveedorService.CompararPreciosAsync(_productoId.Value);
                    grid.Rows.Clear();
                    foreach (var pr in precios)
                        grid.Rows.Add(pr.Nombre, pr.Telefono, pr.PrecioCompra);
                }
            }
            catch (Exception ex)
            {
                lblError.ForeColor = UiTheme.Error;
                lblError.Text = Textos.Inventario.NoSeGuardoPrecioPrefijo + ex.Message;
            }
        }

        // ============ Carga inicial de las secciones (producto existente) ============

        private async Task CargarDetalleRepuestoAsync()
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

                var proveedores = await ProveedorService.ListarAsync(true, null, 1, 500);
                _cboProveedor.DataSource = proveedores.Proveedores;

                var precios = await ProveedorService.CompararPreciosAsync(_productoId.Value);
                _gridPrecios.Rows.Clear();
                foreach (var pr in precios)
                    _gridPrecios.Rows.Add(pr.Nombre, pr.Telefono, pr.PrecioCompra);
            }
            catch (Exception ex)
            {
                _lblErrorRepuesto.Text = Textos.Inventario.NoSeCargoDetalleRepuestoPrefijo + ex.Message;
            }
        }
    }
}
