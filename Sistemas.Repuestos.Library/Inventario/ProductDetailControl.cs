using System;
using System.Drawing;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
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
            var pnlEncabezado = new Panel { Dock = DockStyle.Top, Height = 92, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Xxl, UiTheme.Espacio.Xs, 0, 0) };

            _lnkVolver = new LinkLabel { Text = Textos.Inventario.EnlaceVolver, Dock = DockStyle.Top, Height = 20 };
            _lnkVolver.Click += (s, e) => Volver?.Invoke(this, EventArgs.Empty);

            var pnlNombreCodigo = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, UiTheme.Espacio.Sm, 0, 0) };

            var pnlNombre = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xxl, 0) };
            _lblNombreVista = new Label
            {
                Text = productoExistente?.Nombre ?? string.Empty,
                Font = UiTheme.FuenteTitulo,
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Visible = productoExistente != null
            };
            _lblCampoNombre = new Label { Text = Textos.Inventario.CampoNombre, Dock = DockStyle.Top, Height = 18, Visible = productoExistente == null };
            _txtNombre = new TextBox
            {
                Text = productoExistente?.Nombre ?? string.Empty,
                Font = UiTheme.FuenteTitulo,
                Dock = DockStyle.Top,
                Size = new Size(400, 32),
                Visible = productoExistente == null
            };
            pnlNombre.Controls.Add(_txtNombre);
            pnlNombre.Controls.Add(_lblCampoNombre);
            pnlNombre.Controls.Add(_lblNombreVista);

            var pnlCodigo = new Panel { AutoSize = true };
            _lblCodigoVista = new Label { Text = productoExistente?.Codigo ?? string.Empty, ForeColor = UiTheme.TextoTenue, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Md, 0, 0), Visible = productoExistente != null };
            _lblCampoCodigo = new Label { Text = Textos.Inventario.CampoCodigo, Dock = DockStyle.Top, Height = 18, Visible = productoExistente == null };
            _txtCodigo = new TextBox { Text = productoExistente?.Codigo ?? string.Empty, Dock = DockStyle.Top, Width = 180, Height = UiTheme.Medidas.AlturaControl, Visible = productoExistente == null };
            pnlCodigo.Controls.Add(_txtCodigo);
            pnlCodigo.Controls.Add(_lblCampoCodigo);
            pnlCodigo.Controls.Add(_lblCodigoVista);

            pnlNombreCodigo.Controls.AddRange(new Control[] { pnlNombre, pnlCodigo });

            var pnlBotones = new FlowLayoutPanel
            {
                Dock = DockStyle.Right,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                Padding = new Padding(0, UiTheme.Espacio.Xxl + UiTheme.Espacio.Xs, UiTheme.Espacio.Lg, 0)
            };

            _btnCancelar = Botones.CrearSecundario(Textos.Comun.BotonCancelar);
            _btnCancelar.Click += (s, e) => Cancelar();

            _btnGuardar = Botones.CrearPrimario(Textos.Comun.BotonGuardar);
            _btnGuardar.Click += async (s, e) => await GuardarGeneralAsync();

            _btnAgregarAPack = Botones.CrearSecundario(Textos.Inventario.BotonAgregarAPack);
            _btnAgregarAPack.Click += BtnAgregarAPack_Click;

            _btnEditar = Botones.CrearPrimario(Textos.Comun.BotonEditar);
            _btnEditar.Click += (s, e) => EntrarModoEdicion();

            // Orden de agregado = orden visual izquierda→derecha dentro del panel.
            pnlBotones.Controls.AddRange(new Control[] { _btnEditar, _btnAgregarAPack, _btnGuardar, _btnCancelar });

            pnlEncabezado.Controls.Add(pnlBotones);
            pnlEncabezado.Controls.Add(pnlNombreCodigo);
            pnlEncabezado.Controls.Add(_lnkVolver);

            // ============ Sección General ============
            // Con toda la pantalla disponible (ya no es un diálogo de
            // 640px), un formulario denso se ve amontonado en una esquina —
            // más aire entre filas y columnas es lo que hace que se sienta
            // ordenado, no solo que no se solape.
            var pnlGeneral = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Xxl, UiTheme.Espacio.Md, 0, 0), AutoSize = true };

            var lblDescripcion = new Label { Text = Textos.Inventario.CampoDescripcion, Dock = DockStyle.Top, Height = 20 };
            _txtDescripcion = new TextBox { Text = productoExistente?.Descripcion, Dock = DockStyle.Top, Width = 760, Height = 60, Multiline = true, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var filaPrecio = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var grupoPrecio = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xxl, 0) };
            var lblPrecio = new Label { Text = Textos.Inventario.CampoPrecioUnitario, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _numPrecio = new NumericUpDown { Dock = DockStyle.Top, Width = 180, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = 999999, ThousandsSeparator = true, Value = productoExistente?.PrecioUnitario ?? 0 };
            grupoPrecio.Controls.Add(_numPrecio);
            grupoPrecio.Controls.Add(lblPrecio);

            var grupoCategoria = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xxl, 0) };
            var lblCategoria = new Label { Text = Textos.Inventario.CampoCategoria, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            var pnlCategoriaCombo = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            _cboCategoria = new ComboBox
            {
                Width = 280, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(CategoriaDto.Nombre), ValueMember = nameof(CategoriaDto.Id),
                Margin = new Padding(0, 0, UiTheme.Espacio.Xs, 0)
            };
            var btnNuevaCategoria = Botones.CrearSecundario("+");
            btnNuevaCategoria.Width = 32;
            btnNuevaCategoria.Click += BtnNuevaCategoria_Click;
            pnlCategoriaCombo.Controls.AddRange(new Control[] { _cboCategoria, btnNuevaCategoria });
            grupoCategoria.Controls.Add(pnlCategoriaCombo);
            grupoCategoria.Controls.Add(lblCategoria);

            var grupoStockActual = new Panel { AutoSize = true };
            var lblStockActual = new Label { Text = Textos.Inventario.CampoStockActual, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _lblStockActualValor = new Label { Text = "—", Dock = DockStyle.Top, Height = 22, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold) };
            grupoStockActual.Controls.Add(_lblStockActualValor);
            grupoStockActual.Controls.Add(lblStockActual);

            filaPrecio.Controls.AddRange(new Control[] { grupoPrecio, grupoCategoria, grupoStockActual });

            var filaTasas = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xl) };

            var grupoTasaIsv = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xxl, 0) };
            var lblTasaIsv = new Label { Text = Textos.Inventario.CampoTasaIsv, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _cboTasaIsv = new ComboBox { Dock = DockStyle.Top, Width = 140, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList };
            _cboTasaIsv.Items.AddRange(new object[] { "0", "15", "18" });
            _cboTasaIsv.SelectedItem = productoExistente != null ? ((int)productoExistente.TasaISV).ToString() : "15";
            grupoTasaIsv.Controls.Add(_cboTasaIsv);
            grupoTasaIsv.Controls.Add(lblTasaIsv);

            var grupoUnidadMedida = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Xxl, 0) };
            var lblUnidadMedida = new Label { Text = Textos.Inventario.CampoUnidadMedida, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _cboUnidadMedida = new ComboBox
            {
                Dock = DockStyle.Top, Width = 220, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(UnidadMedidaDto.Nombre), ValueMember = nameof(UnidadMedidaDto.Id)
            };
            _cboUnidadMedida.SelectedIndexChanged += (s, e) =>
            {
                if (_cboUnidadMedida.SelectedItem is UnidadMedidaDto unidad)
                    CantidadFormatter.AplicarModoCantidad(_numStockMinimo, unidad.PermiteFraccion);
            };
            grupoUnidadMedida.Controls.Add(_cboUnidadMedida);
            grupoUnidadMedida.Controls.Add(lblUnidadMedida);

            var grupoStockMinimo = new Panel { AutoSize = true };
            var lblStockMinimo = new Label { Text = Textos.Inventario.CampoStockMinimo, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _numStockMinimo = new NumericUpDown { Dock = DockStyle.Top, Width = 160, Height = UiTheme.Medidas.AlturaControl, Maximum = 100000, DecimalPlaces = 2, Increment = 0.01m, Value = productoExistente?.StockMinimo ?? 0 };
            grupoStockMinimo.Controls.Add(_numStockMinimo);
            grupoStockMinimo.Controls.Add(lblStockMinimo);

            filaTasas.Controls.AddRange(new Control[] { grupoTasaIsv, grupoUnidadMedida, grupoStockMinimo });

            _chkActivo = new CheckBox { Text = Textos.Comun.CampoActivo, AutoSize = true, Dock = DockStyle.Top, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg), Checked = productoExistente?.Activo ?? true, Visible = productoExistente != null };

            _lblErrorGeneral = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 32, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md) };

            pnlGeneral.Controls.Add(_lblErrorGeneral);
            pnlGeneral.Controls.Add(_chkActivo);
            pnlGeneral.Controls.Add(filaTasas);
            pnlGeneral.Controls.Add(filaPrecio);
            pnlGeneral.Controls.Add(_txtDescripcion);
            pnlGeneral.Controls.Add(lblDescripcion);

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
            var panel = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Sm, 0, 0), AutoSize = true };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionRepuesto, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var grillaCampos = FormularioLayout.CrearGrilla(120);
            txtNumeroParte = new TextBox { Width = 240, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grillaCampos, Textos.Inventario.CampoNumeroParte, txtNumeroParte);
            txtMarcaFabricante = new TextBox { Width = 240, Height = UiTheme.Medidas.AlturaControl };
            FormularioLayout.AgregarCampo(grillaCampos, Textos.Inventario.CampoMarcaFabricante, txtMarcaFabricante);

            chkEsOriginal = new CheckBox { Text = Textos.Inventario.CampoEsOriginal, AutoSize = true, Dock = DockStyle.Top, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm), Checked = true };

            lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 30, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var txtNumeroParteRef = txtNumeroParte; var txtMarcaRef = txtMarcaFabricante; var chkOriginalRef = chkEsOriginal; var lblErrorRef = lblError;
            var btnGuardar = Botones.CrearPrimario(Textos.Comun.BotonGuardar);
            btnGuardar.Dock = DockStyle.Top;
            btnGuardar.Click += async (s, e) => await GuardarRepuestoAsync(txtNumeroParteRef, txtMarcaRef, chkOriginalRef, lblErrorRef);

            panel.Controls.Add(btnGuardar);
            panel.Controls.Add(lblError);
            panel.Controls.Add(chkEsOriginal);
            panel.Controls.Add(grillaCampos);
            panel.Controls.Add(lblTitulo);
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
            var panel = new Panel { Dock = DockStyle.Top, Height = 320, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Sm, UiTheme.Espacio.Md, UiTheme.Espacio.Md) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionVehiculos, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var filaCampos = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblMarcaVeh = new Label { Text = Textos.Inventario.CampoMarca, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            txtMarca = new TextBox { Width = 140, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblModeloVeh = new Label { Text = Textos.Inventario.CampoModelo, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            txtModelo = new TextBox { Width = 140, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblAnioDesde = new Label { Text = Textos.Inventario.CampoAnioDesde, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            numAnioDesde = new NumericUpDown { Width = 80, Height = UiTheme.Medidas.AlturaControl, Minimum = 1950, Maximum = 2100, Value = 2000, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblAnioHasta = new Label { Text = Textos.Inventario.CampoAnioHasta, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            numAnioHasta = new NumericUpDown { Width = 80, Height = UiTheme.Medidas.AlturaControl, Minimum = 1950, Maximum = 2100, Value = 2000, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };

            var gridLocal = new DataGridView { Dock = DockStyle.Fill };
            GridStyler.Aplicar(gridLocal);
            gridLocal.Columns.Add("Marca", "Marca");
            gridLocal.Columns.Add("Modelo", "Modelo");
            gridLocal.Columns.Add("AnioDesde", "Año desde");
            gridLocal.Columns.Add("AnioHasta", "Año hasta");
            grid = gridLocal;

            var txtMarcaRef = txtMarca; var txtModeloRef = txtModelo; var numDesdeRef = numAnioDesde; var numHastaRef = numAnioHasta;
            var btnAgregar = Botones.CrearSecundario(Textos.Comun.BotonAgregar);
            filaCampos.Controls.AddRange(new Control[] { lblMarcaVeh, txtMarca, lblModeloVeh, txtModelo, lblAnioDesde, numAnioDesde, lblAnioHasta, numAnioHasta, btnAgregar });

            lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblErrorRef = lblError; var gridRef = grid;
            btnAgregar.Click += async (s, e) => await AgregarVehiculoAsync(txtMarcaRef, txtModeloRef, numDesdeRef, numHastaRef, lblErrorRef, gridRef);

            panel.Controls.Add(gridLocal);
            panel.Controls.Add(lblError);
            panel.Controls.Add(filaCampos);
            panel.Controls.Add(lblTitulo);
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
            var panel = new Panel { Dock = DockStyle.Top, Height = 260, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Sm, UiTheme.Espacio.Md, UiTheme.Espacio.Md) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionEquivalencias, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var filaCampos = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblNumeroOem = new Label { Text = Textos.Inventario.CampoNumeroOem, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            txtNumeroOem = new TextBox { Width = 200, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblFabricanteOem = new Label { Text = Textos.Inventario.CampoFabricante, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            txtFabricante = new TextBox { Width = 200, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };

            var gridLocal = new DataGridView { Dock = DockStyle.Fill };
            GridStyler.Aplicar(gridLocal);
            gridLocal.Columns.Add("NumeroOEM", "Número OEM");
            gridLocal.Columns.Add("Fabricante", "Fabricante");
            grid = gridLocal;

            var txtNumeroRef = txtNumeroOem; var txtFabRef = txtFabricante;
            var btnAgregar = Botones.CrearSecundario(Textos.Comun.BotonAgregar);
            filaCampos.Controls.AddRange(new Control[] { lblNumeroOem, txtNumeroOem, lblFabricanteOem, txtFabricante, btnAgregar });

            lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblErrorRef = lblError; var gridRef = grid;
            btnAgregar.Click += async (s, e) => await AgregarEquivalenteAsync(txtNumeroRef, txtFabRef, lblErrorRef, gridRef);

            panel.Controls.Add(gridLocal);
            panel.Controls.Add(lblError);
            panel.Controls.Add(filaCampos);
            panel.Controls.Add(lblTitulo);
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
            var panel = new Panel { Dock = DockStyle.Top, Height = 260, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Sm, UiTheme.Espacio.Md, UiTheme.Espacio.Md) };

            var lblTitulo = new Label { Text = Textos.Inventario.SeccionPrecios, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var filaCampos = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblProveedor = new Label { Text = Textos.Comun.CampoProveedor, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            cboProveedor = new ComboBox
            {
                Width = 260, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(TerceroDto.Nombre), ValueMember = nameof(TerceroDto.Id),
                Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0)
            };
            var lblPrecioProveedor = new Label { Text = Textos.Inventario.CampoPrecioCompra, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            numPrecio = new NumericUpDown { Width = 140, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = 999999, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };

            var gridLocal = new DataGridView { Dock = DockStyle.Fill };
            GridStyler.Aplicar(gridLocal);
            gridLocal.Columns.Add("Nombre", "Proveedor");
            gridLocal.Columns.Add("Telefono", "Teléfono");
            var colPrecioCompra = new DataGridViewTextBoxColumn { Name = "PrecioCompra", HeaderText = "Precio de compra" };
            GridStyler.ComoColumnaNumerica(colPrecioCompra);
            gridLocal.Columns.Add(colPrecioCompra);
            grid = gridLocal;

            var cboProveedorRef = cboProveedor; var numPrecioRef = numPrecio;
            var btnGuardar = Botones.CrearSecundario(Textos.Comun.BotonGuardar);
            filaCampos.Controls.AddRange(new Control[] { lblProveedor, cboProveedor, lblPrecioProveedor, numPrecio, btnGuardar });

            lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblErrorRef = lblError; var gridRef = grid;
            btnGuardar.Click += async (s, e) => await GuardarPrecioAsync(cboProveedorRef, numPrecioRef, lblErrorRef, gridRef);

            panel.Controls.Add(gridLocal);
            panel.Controls.Add(lblError);
            panel.Controls.Add(filaCampos);
            panel.Controls.Add(lblTitulo);
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
                var (exito, mensaje) = await TerceroService.GuardarPrecioAsync(
                    _productoId.Value, proveedorId, numPrecio.Value, SessionContext.Current?.UsuarioId);

                lblError.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                lblError.Text = mensaje;

                if (exito)
                {
                    var precios = await TerceroService.CompararPreciosAsync(_productoId.Value);
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

                var proveedores = await TerceroService.ListarProveedoresAsync(true, null, 1, 500);
                _cboProveedor.DataSource = proveedores.Terceros;

                var precios = await TerceroService.CompararPreciosAsync(_productoId.Value);
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
