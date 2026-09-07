using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Terceros
{
    // Grid+toolbar+paginación de terceros, parametrizado por rol: la misma
    // pantalla sirve para el módulo "Proveedores" (esVistaProveedores=true,
    // listando EsProveedor=1) y para "Clientes" (false, EsCliente=1).
    // Reemplaza a ProveedoresControl.
    public sealed class TercerosControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly bool _esVistaProveedores;
        private readonly string _rolMinuscula;

        private readonly TextBox _txtBuscar;
        private readonly CheckBox _chkSoloActivos;
        private readonly DataGridView _grid;
        private readonly PaginacionControl _paginacion;
        private readonly Label _lblEstado;

        public TercerosControl(bool esVistaProveedores)
        {
            _esVistaProveedores = esVistaProveedores;
            _rolMinuscula = esVistaProveedores ? Textos.Terceros.RolProveedorMinuscula : Textos.Terceros.RolClienteMinuscula;

            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new Panel { Dock = DockStyle.Top, Height = 64, BackColor = Color.White };

            var btnNuevo = new Button { Text = Textos.Comun.BotonNuevo, Location = new Point(12, 16), Size = new Size(88, 32) };
            btnNuevo.Click += async (s, e) => await AbrirAltaRapidaAsync();

            var btnEditar = new Button { Text = Textos.Comun.BotonEditar, Location = new Point(108, 16), Size = new Size(88, 32) };
            btnEditar.Click += async (s, e) =>
            {
                var seleccionado = ObtenerSeleccionado();
                if (seleccionado == null)
                {
                    MessageBox.Show(this, string.Format(Textos.Terceros.ErrorSeleccionePrimeroFormato, _rolMinuscula), Textos.Comun.BotonEditar);
                    return;
                }
                await AbrirPerfilAsync(seleccionado);
            };

            _txtBuscar = new TextBox { Location = new Point(220, 18), Size = new Size(220, 26) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _paginacion.Reiniciar(); await CargarAsync(); } };

            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(448, 17), Size = new Size(80, 28) };
            btnBuscar.Click += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            _chkSoloActivos = new CheckBox { Text = Textos.Comun.CampoSoloActivos, AutoSize = true, Location = new Point(540, 22), Checked = true };
            _chkSoloActivos.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };

            pnlToolbar.Controls.AddRange(new Control[] { btnNuevo, btnEditar, _txtBuscar, btnBuscar, _chkSoloActivos });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(TerceroDto.Nombre), HeaderText = "Nombre", FillWeight = 25 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(TerceroDto.Empresa), HeaderText = "Empresa", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(TerceroDto.Telefono), HeaderText = "Teléfono", FillWeight = 13 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(TerceroDto.Correo), HeaderText = "Correo", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(TerceroDto.RTN), HeaderText = "RTN", FillWeight = 12 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(TerceroDto.Activo), HeaderText = "Activo", FillWeight = 10 });
            _grid.CellDoubleClick += async (s, e) =>
            {
                var seleccionado = ObtenerSeleccionado();
                if (seleccionado != null) await AbrirPerfilAsync(seleccionado);
            };

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            _lblEstado = new Label { Dock = DockStyle.Bottom, Height = 24, TextAlign = ContentAlignment.MiddleLeft, Padding = new Padding(12, 0, 0, 0), ForeColor = UiTheme.Error };

            Controls.Add(_grid);
            Controls.Add(_lblEstado);
            Controls.Add(_paginacion);
            Controls.Add(pnlToolbar);

            Load += async (s, e) => await CargarAsync();
        }

        private async Task CargarAsync()
        {
            try
            {
                var busqueda = string.IsNullOrWhiteSpace(_txtBuscar.Text) ? null : _txtBuscar.Text.Trim();
                var (terceros, total) = _esVistaProveedores
                    ? await TerceroService.ListarProveedoresAsync(_chkSoloActivos.Checked, busqueda, _paginacion.Pagina, TamanoPagina)
                    : await TerceroService.ListarClientesAsync(_chkSoloActivos.Checked, busqueda, _paginacion.Pagina, TamanoPagina);

                _grid.DataSource = terceros;
                _paginacion.Actualizar(total, TamanoPagina);
                _lblEstado.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblEstado.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private TerceroDto? ObtenerSeleccionado() => _grid.CurrentRow?.DataBoundItem as TerceroDto;

        private async Task AbrirAltaRapidaAsync()
        {
            using var form = new FormTercero(null, rolProveedorPorDefecto: _esVistaProveedores);
            form.ShowDialog(FindForm());
            await CargarAsync();
        }

        private async Task AbrirPerfilAsync(TerceroDto tercero)
        {
            using var form = new FormPerfilTercero(tercero, vistaCuentasPorPagar: _esVistaProveedores);
            form.ShowDialog(FindForm());
            await CargarAsync();
        }
    }
}
