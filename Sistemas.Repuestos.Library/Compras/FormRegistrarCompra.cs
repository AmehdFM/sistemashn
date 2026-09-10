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

            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 172, BackColor = Color.White };

            var lblProveedor = new Label { Text = Textos.Compras.CampoProveedor, AutoSize = true, Location = new Point(16, 8) };
            _cboProveedor = new ComboBox
            {
                Location = new Point(16, 28), Size = new Size(280, 26), DropDownStyle = ComboBoxStyle.DropDownList,
                DisplayMember = nameof(TerceroDto.Nombre), ValueMember = nameof(TerceroDto.Id)
            };

            var lblNumeroFactura = new Label { Text = Textos.Compras.CampoNumeroFacturaProveedor, AutoSize = true, Location = new Point(310, 8) };
            _txtNumeroFactura = new TextBox { Location = new Point(310, 28), Size = new Size(180, 26) };

            _chkEsCredito = new CheckBox { Text = Textos.Compras.CampoCompraCredito, AutoSize = true, Location = new Point(510, 12) };
            _chkEsCredito.CheckedChanged += (s, e) => _numDiasCredito.Enabled = _chkEsCredito.Checked;

            var lblDias = new Label { Text = Textos.Compras.CampoDiasCredito, AutoSize = true, Location = new Point(510, 36) };
            _numDiasCredito = new NumericUpDown { Location = new Point(600, 34), Size = new Size(70, 26), Minimum = 1, Maximum = 365, Value = 30, Enabled = false };

            var lblBuscar = new Label { Text = Textos.Compras.CampoBuscarProducto, AutoSize = true, Location = new Point(16, 70) };
            _txtBuscarProducto = new TextBox { Location = new Point(16, 90), Size = new Size(200, 26) };
            var btnBuscarProducto = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(222, 89), Size = new Size(80, 28) };
            btnBuscarProducto.Click += BtnBuscarProducto_Click;

            _cboResultadoProducto = new ComboBox { Location = new Point(16, 122), Size = new Size(320, 26), DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true };
            _cboResultadoProducto.Format += (s, e) => { if (e.ListItem is ProductoDto p) e.Value = $"{p.Codigo} — {p.Nombre}"; };
            _cboResultadoProducto.SelectedIndexChanged += (s, e) =>
            {
                if (_cboResultadoProducto.SelectedItem is ProductoDto p)
                    CantidadFormatter.AplicarModoCantidad(_numCantidad, p.PermiteFraccionUnidad);
            };

            var lblCantidad = new Label { Text = Textos.Comun.CampoCantidad, AutoSize = true, Location = new Point(346, 98) };
            _numCantidad = new NumericUpDown { Location = new Point(346, 122), Size = new Size(70, 26), Minimum = 1, Maximum = 100000, Value = 1 };

            var lblCosto = new Label { Text = Textos.Compras.CampoCostoUnitario, AutoSize = true, Location = new Point(426, 98) };
            _numCosto = new NumericUpDown { Location = new Point(426, 122), Size = new Size(100, 26), DecimalPlaces = 2, Maximum = 999999 };

            var btnAgregarLinea = new Button { Text = Textos.Comun.BotonAgregar, Location = new Point(536, 121), Size = new Size(90, 28) };
            btnAgregarLinea.Click += BtnAgregarLinea_Click;

            pnlTop.Controls.AddRange(new Control[]
            {
                lblProveedor, _cboProveedor, lblNumeroFactura, _txtNumeroFactura, _chkEsCredito, lblDias, _numDiasCredito,
                lblBuscar, _txtBuscarProducto, btnBuscarProducto, _cboResultadoProducto, lblCantidad, _numCantidad,
                lblCosto, _numCosto, btnAgregarLinea
            });

            _gridLineas = new DataGridView { DataSource = _lineas };
            GridStyler.Aplicar(_gridLineas);
            _gridLineas.AutoGenerateColumns = false;
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Codigo), HeaderText = "Código", FillWeight = 15 });
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Nombre), HeaderText = "Nombre", FillWeight = 35 });
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.CostoUnitario), HeaderText = "Costo unit.", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _gridLineas.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(LineaCompraDto.Subtotal), HeaderText = "Subtotal", FillWeight = 20, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _gridLineas.CellFormatting += (s, e) =>
            {
                if (_gridLineas.Columns[e.ColumnIndex].DataPropertyName != nameof(LineaCompraDto.Cantidad)) return;
                if (_lineas.Count <= e.RowIndex) return;
                var linea = _lineas[e.RowIndex];
                e.Value = CantidadFormatter.FormatearCantidad(linea.Cantidad, linea.PermiteFraccion);
                e.FormattingApplied = true;
            };

            // Height = 110: btnQuitarLinea (y8-36) + _lblError (y42-66) +
            // _btnRegistrar (y68-102) necesitan 102px de alto, más 8px de
            // margen inferior — con 96 el botón quedaba cortado por el
            // borde del panel.
            var pnlBottom = new Panel { Dock = DockStyle.Bottom, Height = 110, BackColor = Color.White };
            var btnQuitarLinea = new Button { Text = Textos.Compras.BotonQuitarLinea, Location = new Point(16, 8), Size = new Size(120, 28) };
            btnQuitarLinea.Click += (s, e) =>
            {
                if (_gridLineas.CurrentRow?.DataBoundItem is LineaCompraDto linea)
                {
                    _lineas.Remove(linea);
                    ActualizarTotal();
                }
            };

            _lblTotal = new Label { Text = string.Format(Textos.Compras.FormatoTotal, 0m), AutoSize = true, Location = new Point(500, 12), Font = new Font(UiTheme.FuenteBase, FontStyle.Bold) };

            // Anchor Left+Right: a MinimumSize.Width (680) el Width fijo de
            // 680px a partir de x=16 se salía del área visible del panel.
            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(680, 24), Location = new Point(16, 42), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };

            _btnRegistrar = new Button
            {
                Text = Textos.Compras.RegistrarTituloVentana,
                Location = new Point(16, 68),
                Size = new Size(180, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnRegistrar.FlatAppearance.BorderSize = 0;
            _btnRegistrar.Click += BtnRegistrar_Click;

            pnlBottom.Controls.AddRange(new Control[] { btnQuitarLinea, _lblTotal, _lblError, _btnRegistrar });

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
