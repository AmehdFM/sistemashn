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

            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 122, BackColor = Color.White };

            var lblAviso = new Label
            {
                Text = Textos.Inventario.ArmarPaqueteAviso,
                AutoSize = true,
                Location = new Point(16, 8),
                ForeColor = UiTheme.TextoTenue
            };

            var lblBuscar = new Label { Text = Textos.Inventario.CampoBuscarComponente, AutoSize = true, Location = new Point(16, 32) };
            _txtBuscar = new TextBox { Location = new Point(16, 52), Size = new Size(200, 26) };
            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(222, 51), Size = new Size(80, 28) };
            btnBuscar.Click += BtnBuscar_Click;

            _cboResultado = new ComboBox { Location = new Point(16, 84), Size = new Size(320, 26), DropDownStyle = ComboBoxStyle.DropDownList, FormattingEnabled = true };
            _cboResultado.Format += (s, e) => { if (e.ListItem is ProductoDto p) e.Value = $"{p.Codigo} — {p.Nombre}"; };

            var lblCantidad = new Label { Text = Textos.Comun.CampoCantidad, AutoSize = true, Location = new Point(346, 60) };
            _numCantidad = new NumericUpDown { Location = new Point(346, 84), Size = new Size(70, 26), Minimum = 1, Maximum = 10000, Value = 1 };

            var btnAgregar = new Button { Text = Textos.Comun.BotonAgregar, Location = new Point(426, 83), Size = new Size(90, 28) };
            btnAgregar.Click += BtnAgregar_Click;

            pnlTop.Controls.AddRange(new Control[] { lblAviso, lblBuscar, _txtBuscar, btnBuscar, _cboResultado, lblCantidad, _numCantidad, btnAgregar });

            _gridComponentes = new DataGridView { DataSource = _componentes };
            GridStyler.Aplicar(_gridComponentes);
            _gridComponentes.AutoGenerateColumns = false;
            _gridComponentes.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ComponentePaqueteDto.Codigo), HeaderText = "Código", FillWeight = 20 });
            _gridComponentes.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ComponentePaqueteDto.Nombre), HeaderText = "Nombre", FillWeight = 50 });
            _gridComponentes.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(ComponentePaqueteDto.Cantidad), HeaderText = "Cantidad", FillWeight = 15 });

            // Height = 110: btnQuitar (y8-36) + _lblError (y40-64) +
            // _btnGuardar (y68-102) necesitan 102px de alto, más 8px de
            // margen inferior — con 84 el botón quedaba cortado por el
            // borde del panel.
            var pnlBottom = new Panel { Dock = DockStyle.Bottom, Height = 110, BackColor = Color.White };
            var btnQuitar = new Button { Text = Textos.Inventario.BotonQuitarSeleccionado, Location = new Point(16, 8), Size = new Size(160, 28) };
            btnQuitar.Click += (s, e) =>
            {
                if (_gridComponentes.CurrentRow?.DataBoundItem is ComponentePaqueteDto comp)
                    _componentes.Remove(comp);
            };

            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(600, 24), Location = new Point(16, 40) };

            _btnGuardar = new Button
            {
                Text = Textos.Inventario.BotonGuardarPaquete,
                Location = new Point(16, 68),
                Size = new Size(160, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnGuardar.FlatAppearance.BorderSize = 0;
            _btnGuardar.Click += BtnGuardar_Click;

            pnlBottom.Controls.AddRange(new Control[] { btnQuitar, _lblError, _btnGuardar });

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
                existente.Cantidad += (int)_numCantidad.Value;
                _componentes.ResetItem(_componentes.IndexOf(existente));
            }
            else
            {
                _componentes.Add(new ComponentePaqueteDto
                {
                    ComponenteProductoId = seleccionado.Id,
                    Codigo = seleccionado.Codigo,
                    Nombre = seleccionado.Nombre,
                    Cantidad = (int)_numCantidad.Value
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
