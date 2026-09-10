using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
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
        private readonly EstadoListaControl _estado;
        private readonly PaginacionControl _paginacion;
        private EstadoLista _estadoActual;

        public TercerosControl(bool esVistaProveedores)
        {
            _esVistaProveedores = esVistaProveedores;
            _rolMinuscula = esVistaProveedores ? Textos.Terceros.RolProveedorMinuscula : Textos.Terceros.RolClienteMinuscula;

            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Md, UiTheme.Espacio.Md, UiTheme.Espacio.Sm)
            };
            var btnNuevo = Botones.CrearToolbar(Textos.Comun.BotonNuevo, primario: true);
            btnNuevo.Click += async (s, e) => await AbrirAltaRapidaAsync();
            var btnEditar = Botones.CrearToolbar(Textos.Comun.BotonEditar);
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
            pnlToolbar.Controls.AddRange(new Control[] { btnNuevo, btnEditar });

            var pnlFiltros = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(UiTheme.Espacio.Md, 0, UiTheme.Espacio.Md, UiTheme.Espacio.Md)
            };
            _txtBuscar = new TextBox { Width = 220, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _paginacion.Reiniciar(); await CargarAsync(); } };
            var btnBuscar = Botones.CrearSecundario(Textos.Comun.BotonBuscar);
            btnBuscar.Click += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            _chkSoloActivos = new CheckBox { Text = Textos.Comun.CampoSoloActivos, AutoSize = true, Checked = true, Margin = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Sm + 2, 0, 0) };
            _chkSoloActivos.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            pnlFiltros.Controls.AddRange(new Control[] { _txtBuscar, btnBuscar, _chkSoloActivos });

            _grid = new DataGridView { Visible = false };
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

            _estado = new EstadoListaControl();
            _estado.AccionSolicitada += async (s, e) =>
            {
                switch (_estadoActual)
                {
                    case EstadoLista.VacioInicial:
                        await AbrirAltaRapidaAsync();
                        break;
                    case EstadoLista.VacioPorFiltro:
                        _txtBuscar.Clear();
                        _paginacion.Reiniciar();
                        await CargarAsync();
                        break;
                    case EstadoLista.Error:
                        await CargarAsync();
                        break;
                }
            };

            var pnlGrid = new Panel { Dock = DockStyle.Fill };
            pnlGrid.Controls.Add(_grid);
            pnlGrid.Controls.Add(_estado);

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            Controls.Add(pnlGrid);
            Controls.Add(_paginacion);
            Controls.Add(pnlFiltros);
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

                _paginacion.Actualizar(total, TamanoPagina);

                if (terceros.Count == 0)
                {
                    _grid.Visible = false;
                    _estadoActual = busqueda != null ? EstadoLista.VacioPorFiltro : EstadoLista.VacioInicial;
                    _estado.Mostrar(
                        _estadoActual,
                        _estadoActual == EstadoLista.VacioPorFiltro
                            ? string.Format(Textos.Terceros.SinResultadosBusquedaFormato, _rolMinuscula)
                            : string.Format(Textos.Terceros.SinRegistrosFormato, _rolMinuscula),
                        _estadoActual == EstadoLista.VacioPorFiltro ? Textos.Comun.BotonLimpiarFiltros : Textos.Comun.BotonNuevo);
                    return;
                }

                _grid.DataSource = terceros;
                _grid.Visible = true;
                _estado.Ocultar();
            }
            catch (Exception ex)
            {
                _grid.Visible = false;
                _estadoActual = EstadoLista.Error;
                _estado.Mostrar(EstadoLista.Error, Textos.Comun.NoSeConectoBdPrefijo + ex.Message, Textos.Comun.BotonReintentar);
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
