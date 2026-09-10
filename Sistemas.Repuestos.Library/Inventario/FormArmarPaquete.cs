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

namespace Sistemas.Repuestos.Library.Inventario
{
    public sealed class FormArmarPaquete : FormBase
    {
        private readonly ProductoDto _paquete;
        private readonly BindingList<ComponentePaqueteDto> _componentes = new();

        private readonly TextBox _txtBuscar;
        private readonly ComboBox _cboResultado;
        private readonly NumericUpDown _numCantidad;
        private readonly DataGridView _gridComponentes;
        private readonly Label _lblError;
        private readonly Button _btnGuardar;

        public FormArmarPaquete(ProductoDto paquete)
        {
            _paquete = paquete;

            Text = string.Format(Textos.Inventario.ArmarPaqueteTituloFormato, paquete.Codigo, paquete.Nombre);
            ClientSize = new Size(640, 480);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(560, 420);

            var pnlTop = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var lblAviso = new Label
            {
                Text = Textos.Inventario.ArmarPaqueteAviso,
                Dock = DockStyle.Top,
                Height = 20,
                ForeColor = UiTheme.TextoTenue,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm)
            };

            var pnlBusqueda = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblBuscar = new Label { Text = Textos.Inventario.CampoBuscarComponente, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _txtBuscar = new TextBox { Width = 200, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            var btnBuscar = Botones.CrearSecundario(Textos.Comun.BotonBuscar);
            btnBuscar.Click += BtnBuscar_Click;
            pnlBusqueda.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, btnBuscar });

            var pnlSeleccion = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            _cboResultado = new ComboBox { Width = 320, Height = UiTheme.Medidas.AlturaControl, DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            _cboResultado.Format += (s, e) => { if (e.ListItem is ProductoDto p) e.Value = $"{p.Codigo} — {p.Nombre}"; };
            _cboResultado.SelectedIndexChanged += (s, e) =>
            {
                if (_cboResultado.SelectedItem is ProductoDto p)
                    CantidadFormatter.AplicarModoCantidad(_numCantidad, p.PermiteFraccionUnidad);
            };
            var lblCantidad = new Label { Text = Textos.Comun.CampoCantidad, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _numCantidad = new NumericUpDown { Width = 70, Height = UiTheme.Medidas.AlturaControl, Minimum = 1, Maximum = 10000, Value = 1, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            var btnAgregar = Botones.CrearSecundario(Textos.Comun.BotonAgregar);
            btnAgregar.Click += BtnAgregar_Click;
            pnlSeleccion.Controls.AddRange(new Control[] { _cboResultado, lblCantidad, _numCantidad, btnAgregar });

            pnlTop.Controls.Add(pnlSeleccion);
            pnlTop.Controls.Add(pnlBusqueda);
            pnlTop.Controls.Add(lblAviso);

            _gridComponentes = new DataGridView { DataSource = _componentes };
            GridStyler.Aplicar(_gridComponentes);
            _gridComponentes.AutoGenerateColumns = false;
            _gridComponentes.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ComponentePaqueteDto.Codigo), HeaderText = "Código", FillWeight = 20 });
            _gridComponentes.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ComponentePaqueteDto.Nombre), HeaderText = "Nombre", FillWeight = 50 });
            _gridComponentes.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ComponentePaqueteDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });
            _gridComponentes.CellFormatting += (s, e) =>
            {
                if (_gridComponentes.Columns[e.ColumnIndex].DataPropertyName != nameof(ComponentePaqueteDto.Cantidad)) return;
                if (_componentes.Count <= e.RowIndex) return;
                var comp = _componentes[e.RowIndex];
                e.Value = CantidadFormatter.FormatearCantidad(comp.Cantidad, comp.PermiteFraccion);
                e.FormattingApplied = true;
            };

            var pnlBottom = new Panel { Dock = DockStyle.Bottom, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var pnlAcciones = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var btnQuitar = Botones.CrearSecundario(Textos.Inventario.BotonQuitarSeleccionado);
            btnQuitar.Click += (s, e) =>
            {
                if (_gridComponentes.CurrentRow?.DataBoundItem is ComponentePaqueteDto comp)
                    _componentes.Remove(comp);
            };
            _btnGuardar = Botones.CrearPrimario(Textos.Inventario.BotonGuardarPaquete);
            _btnGuardar.Click += BtnGuardar_Click;
            pnlAcciones.Controls.AddRange(new Control[] { btnQuitar, _btnGuardar });

            _lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 24 };

            pnlBottom.Controls.Add(_lblError);
            pnlBottom.Controls.Add(pnlAcciones);

            Controls.Add(_gridComponentes);
            Controls.Add(pnlBottom);
            Controls.Add(pnlTop);
        }

        private async void BtnBuscar_Click(object? sender, EventArgs e)
        {
            var busqueda = _txtBuscar.Text.Trim();
            if (busqueda.Length == 0) return;

            try
            {
                var (productos, _) = await ProductService.ListarAsync(true, null, busqueda, 1, 30);
                _cboResultado.DataSource = productos.Where(p => p.Id != _paquete.Id).ToList();
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Comun.NoSePudoBuscarPrefijo + ex.Message);
            }
        }

        private void BtnAgregar_Click(object? sender, EventArgs e)
        {
            if (_cboResultado.SelectedItem is not ProductoDto seleccionado)
            {
                _lblError.Text = Textos.Comun.ErrorBusqueSeleccioneProductoPrimero;
                return;
            }

            var existente = _componentes.FirstOrDefault(c => c.ComponenteProductoId == seleccionado.Id);
            if (existente != null)
            {
                existente.Cantidad += _numCantidad.Value;
                _componentes.ResetItem(_componentes.IndexOf(existente));
            }
            else
            {
                _componentes.Add(new ComponentePaqueteDto
                {
                    ComponenteProductoId = seleccionado.Id,
                    Codigo = seleccionado.Codigo,
                    Nombre = seleccionado.Nombre,
                    Cantidad = _numCantidad.Value,
                    PermiteFraccion = seleccionado.PermiteFraccionUnidad
                });
            }

            _lblError.Text = string.Empty;
        }

        private async void BtnGuardar_Click(object? sender, EventArgs e)
        {
            if (_componentes.Count == 0)
            {
                _lblError.Text = Textos.Inventario.ErrorAgregueUnComponente;
                return;
            }

            _btnGuardar.Enabled = false;
            try
            {
                var (exito, mensaje) = await PaqueteService.ArmarAsync(
                    _paquete.Id, _componentes.ToList(), SessionContext.Current?.UsuarioId ?? 0);

                _lblError.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblError.Text = mensaje;

                if (exito)
                {
                    DialogResult = DialogResult.OK;
                    Close();
                }
            }
            catch (Exception ex)
            {
                MostrarError(Textos.Inventario.NoSeArmoPaquetePrefijo + ex.Message);
            }
            finally
            {
                _btnGuardar.Enabled = true;
            }
        }
    }
}
