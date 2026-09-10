using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Compras
{
    public sealed class FormRegistrarCompra : FormBase
    {
        private readonly BindingList<LineaCompraDto> _lineas = new();

        private readonly ComboBox _cboProveedor;
        private readonly TextBox _txtNumeroFactura;
        private readonly CheckBox _chkEsCredito;
        private readonly NumericUpDown _numDiasCredito;

        private readonly TextBox _txtBuscarProducto;
        private readonly ComboBox _cboResultadoProducto;
        private readonly NumericUpDown _numCantidad;
        private readonly NumericUpDown _numCosto;

        private readonly DataGridView _gridLineas;
        private readonly Label _lblTotal;
        private readonly Label _lblError;
        private readonly Button _btnRegistrar;

        public FormRegistrarCompra()
        {
            Text = Textos.Compras.RegistrarTituloVentana;
            ClientSize = new Size(720, 560);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(680, 480);

            var pnlTop = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var filaProveedor = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Md) };
            var grupoProveedor = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblProveedor = new Label { Text = Textos.Compras.CampoProveedor, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _cboProveedor = new ComboBox
            {
                Dock = DockStyle.Top, Width = 280, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(TerceroDto.Nombre), ValueMember = nameof(TerceroDto.Id)
            };
            grupoProveedor.Controls.Add(_cboProveedor);
            grupoProveedor.Controls.Add(lblProveedor);

            var grupoFactura = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblNumeroFactura = new Label { Text = Textos.Compras.CampoNumeroFacturaProveedor, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _txtNumeroFactura = new TextBox { Dock = DockStyle.Top, Width = 180, Height = UiTheme.Medidas.AlturaControl };
            grupoFactura.Controls.Add(_txtNumeroFactura);
            grupoFactura.Controls.Add(lblNumeroFactura);

            var grupoCredito = new Panel { AutoSize = true };
            _chkEsCredito = new CheckBox { Text = Textos.Compras.CampoCompraCredito, AutoSize = true, Dock = DockStyle.Top, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Xs) };
            _chkEsCredito.CheckedChanged += (s, e) => _numDiasCredito.Enabled = _chkEsCredito.Checked;
            var filaDias = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            var lblDias = new Label { Text = Textos.Compras.CampoDiasCredito, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Xs, 0) };
            _numDiasCredito = new NumericUpDown { Width = 70, Height = UiTheme.Medidas.AlturaControl, Minimum = 1, Maximum = 365, Value = 30, Enabled = false };
            filaDias.Controls.AddRange(new Control[] { lblDias, _numDiasCredito });
            grupoCredito.Controls.Add(filaDias);
            grupoCredito.Controls.Add(_chkEsCredito);

            filaProveedor.Controls.AddRange(new Control[] { grupoProveedor, grupoFactura, grupoCredito });

            var filaProducto = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            var grupoBuscar = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblBuscar = new Label { Text = Textos.Compras.CampoBuscarProducto, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            var filaBuscar = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            _txtBuscarProducto = new TextBox { Width = 200, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Xs, 0) };
            var btnBuscarProducto = Botones.CrearSecundario(Textos.Comun.BotonBuscar);
            btnBuscarProducto.Click += BtnBuscarProducto_Click;
            filaBuscar.Controls.AddRange(new Control[] { _txtBuscarProducto, btnBuscarProducto });
            grupoBuscar.Controls.Add(filaBuscar);
            grupoBuscar.Controls.Add(lblBuscar);

            var grupoResultado = new Panel { AutoSize = true, Margin = new Padding(0, 18, UiTheme.Espacio.Md, 0) };
            _cboResultadoProducto = new ComboBox { Dock = DockStyle.Top, Width = 320, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true };
            _cboResultadoProducto.Format += (s, e) => { if (e.ListItem is ProductoDto p) e.Value = $"{p.Codigo} — {p.Nombre}"; };
            _cboResultadoProducto.SelectedIndexChanged += (s, e) =>
            {
                if (_cboResultadoProducto.SelectedItem is ProductoDto p)
                    CantidadFormatter.AplicarModoCantidad(_numCantidad, p.PermiteFraccionUnidad);
            };
            grupoResultado.Controls.Add(_cboResultadoProducto);

            var grupoCantidad = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblCantidad = new Label { Text = Textos.Comun.CampoCantidad, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _numCantidad = new NumericUpDown { Dock = DockStyle.Top, Width = 70, Height = UiTheme.Medidas.AlturaControl, Minimum = 1, Maximum = 100000, Value = 1 };
            grupoCantidad.Controls.Add(_numCantidad);
            grupoCantidad.Controls.Add(lblCantidad);

            var grupoCosto = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblCosto = new Label { Text = Textos.Compras.CampoCostoUnitario, Dock = DockStyle.Top, Height = 18, ForeColor = UiTheme.TextoTenue };
            _numCosto = new NumericUpDown { Dock = DockStyle.Top, Width = 100, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = 999999 };
            grupoCosto.Controls.Add(_numCosto);
            grupoCosto.Controls.Add(lblCosto);

            var grupoAgregar = new Panel { AutoSize = true, Margin = new Padding(0, 18, 0, 0) };
            var btnAgregarLinea = Botones.CrearPrimario(Textos.Comun.BotonAgregar);
            btnAgregarLinea.Click += BtnAgregarLinea_Click;
            grupoAgregar.Controls.Add(btnAgregarLinea);

            filaProducto.Controls.AddRange(new Control[] { grupoBuscar, grupoResultado, grupoCantidad, grupoCosto, grupoAgregar });

            pnlTop.Controls.Add(filaProducto);
            pnlTop.Controls.Add(filaProveedor);

            _gridLineas = new DataGridView { DataSource = _lineas };
            GridStyler.Aplicar(_gridLineas);
            _gridLineas.AutoGenerateColumns = false;
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Codigo), HeaderText = "Código", FillWeight = 15 });
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Nombre), HeaderText = "Nombre", FillWeight = 35 });
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });
            var colCosto = new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.CostoUnitario), HeaderText = "Costo unit.", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colCosto);
            _gridLineas.Columns.Add(colCosto);
            var colSubtotal = new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Subtotal), HeaderText = "Subtotal", FillWeight = 20 };
            GridStyler.ComoColumnaNumerica(colSubtotal);
            _gridLineas.Columns.Add(colSubtotal);
            _gridLineas.CellFormatting += (s, e) =>
            {
                if (_gridLineas.Columns[e.ColumnIndex].DataPropertyName != nameof(LineaCompraDto.Cantidad)) return;
                if (_lineas.Count <= e.RowIndex) return;
                var linea = _lineas[e.RowIndex];
                e.Value = CantidadFormatter.FormatearCantidad(linea.Cantidad, linea.PermiteFraccion);
                e.FormattingApplied = true;
            };

            var pnlBottom = new Panel { Dock = DockStyle.Bottom, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var filaAcciones = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var btnQuitarLinea = Botones.CrearSecundario(Textos.Compras.BotonQuitarLinea);
            btnQuitarLinea.Click += (s, e) =>
            {
                if (_gridLineas.CurrentRow?.DataBoundItem is LineaCompraDto linea)
                {
                    _lineas.Remove(linea);
                    ActualizarTotal();
                }
            };
            _lblTotal = new Label
            {
                Text = string.Format(Textos.Compras.FormatoTotal, 0m),
                AutoSize = true,
                Font = new Font(UiTheme.FuenteBase, 14f, FontStyle.Bold),
                Margin = new Padding(UiTheme.Espacio.Xxl, UiTheme.Espacio.Xs, 0, 0)
            };
            filaAcciones.Controls.AddRange(new Control[] { btnQuitarLinea, _lblTotal });

            _lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            _btnRegistrar = Botones.CrearPrimario(Textos.Compras.RegistrarTituloVentana);
            _btnRegistrar.AutoSize = false;
            _btnRegistrar.Width = 200;
            _btnRegistrar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnRegistrar.Click += BtnRegistrar_Click;

            pnlBottom.Controls.Add(_btnRegistrar);
            pnlBottom.Controls.Add(_lblError);
            pnlBottom.Controls.Add(filaAcciones);

            Controls.Add(_gridLineas);
            Controls.Add(pnlBottom);
            Controls.Add(pnlTop);

            Load += FormRegistrarCompra_Load;
        }

        private async void FormRegistrarCompra_Load(object? sender, EventArgs e)
        {
            try
            {
                var (proveedores, totalProveedores) = await TerceroService.ListarProveedoresAsync(true, null, 1, 500);
                _cboProveedor.DataSource = proveedores;

                // El combo carga hasta 500 proveedores de una vez: si hay más
                // activos que eso, se avisa en vez de truncar en silencio.
                if (totalProveedores > proveedores.Count)
                    _lblError.Text = string.Format(Textos.Compras.AvisoTopeProveedoresFormato, totalProveedores);
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Compras.NoSeCargaronProveedoresPrefijo + ex.Message);
            }
        }

        private async void BtnBuscarProducto_Click(object? sender, EventArgs e)
        {
            var busqueda = _txtBuscarProducto.Text.Trim();
            if (busqueda.Length == 0) return;

            try
            {
                var (productos, _) = await ProductService.ListarAsync(true, null, busqueda, 1, 30);
                _cboResultadoProducto.DataSource = productos;
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoBuscarPrefijo + ex.Message);
            }
        }

        private void BtnAgregarLinea_Click(object? sender, EventArgs e)
        {
            if (_cboResultadoProducto.SelectedItem is not ProductoDto producto)
            {
                _lblError.Text = Textos.Comun.ErrorBusqueSeleccioneProductoPrimero;
                return;
            }

            _lineas.Add(new LineaCompraDto
            {
                ProductoId = producto.Id,
                Codigo = producto.Codigo,
                Nombre = producto.Nombre,
                Cantidad = _numCantidad.Value,
                PermiteFraccion = producto.PermiteFraccionUnidad,
                CostoUnitario = _numCosto.Value
            });

            _lblError.Text = string.Empty;
            ActualizarTotal();
        }

        private void ActualizarTotal() => _lblTotal.Text = string.Format(Textos.Compras.FormatoTotal, _lineas.Sum(l => l.Subtotal));

        private async void BtnRegistrar_Click(object? sender, EventArgs e)
        {
            if (_cboProveedor.SelectedValue is not int proveedorId)
            {
                _lblError.Text = Textos.Compras.ErrorSeleccioneProveedor;
                return;
            }

            if (_lineas.Count == 0)
            {
                _lblError.Text = Textos.Compras.ErrorAgregueUnaLinea;
                return;
            }

            _btnRegistrar.Enabled = false;
            try
            {
                var (exito, mensaje, _) = await CompraService.RegistrarAsync(
                    proveedorId,
                    string.IsNullOrWhiteSpace(_txtNumeroFactura.Text) ? null : _txtNumeroFactura.Text.Trim(),
                    _chkEsCredito.Checked,
                    _chkEsCredito.Checked ? (int)_numDiasCredito.Value : null,
                    _lineas.ToList(),
                    SessionContext.Current?.UsuarioId ?? 0);

                if (exito)
                {
                    MostrarInfo(mensaje);
                    DialogResult = DialogResult.OK;
                    Close();
                }
                else
                {
                    _lblError.Text = mensaje;
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Compras.NoSeRegistroCompraPrefijo + ex.Message);
            }
            finally
            {
                _btnRegistrar.Enabled = true;
            }
        }
    }
}
