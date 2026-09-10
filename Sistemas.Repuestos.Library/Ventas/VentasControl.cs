using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Ventas
{
    // Historial de ventas: buscar por factura, ver el listado y anular una
    // venta con motivo. Antes vivía como un diálogo (FormHistorialVentas)
    // que se abría desde POS; ahora es el contenido propio del módulo
    // "Ventas" de la barra lateral — el cobro rápido en sí vive en POS.
    public sealed class VentasControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly TextBox _txtBuscar;
        private readonly CheckBox _chkSoloVigentes;
        private readonly DataGridView _grid;
        private readonly EstadoListaControl _estado;
        private readonly PaginacionControl _paginacion;
        private readonly TextBox _txtMotivo;
        private readonly Label _lblError;
        private readonly Button _btnAnular;
        private EstadoLista _estadoActual;

        public VentasControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlTop = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(UiTheme.Espacio.Md)
            };
            var lblBuscar = new Label { Text = Textos.Ventas.CampoNumeroFactura, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _txtBuscar = new TextBox { Width = 220, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _paginacion.Reiniciar(); await CargarAsync(); } };
            var btnBuscar = Botones.CrearSecundario(Textos.Comun.BotonBuscar);
            btnBuscar.Click += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            _chkSoloVigentes = new CheckBox { Text = Textos.Ventas.CampoSoloVigentes, AutoSize = true, Checked = true, Margin = new Padding(UiTheme.Espacio.Md, UiTheme.Espacio.Sm + 2, UiTheme.Espacio.Md, 0) };
            _chkSoloVigentes.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            var btnExportar = Botones.CrearSecundario(Textos.Ventas.BotonExportarExcel);
            btnExportar.Click += BtnExportar_Click;
            pnlTop.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, btnBuscar, _chkSoloVigentes, btnExportar });

            _grid = new DataGridView { Visible = false };
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.NumeroFactura), HeaderText = "N° factura", FillWeight = 25 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.Fecha), HeaderText = "Fecha", FillWeight = 18, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            var colTotal = new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.Total), HeaderText = "Total", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colTotal);
            _grid.Columns.Add(colTotal);
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(VentaDto.EsCredito), HeaderText = "Crédito", FillWeight = 12 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.MetodoPago), HeaderText = "Método de pago", FillWeight = 15 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(VentaDto.Anulada), HeaderText = "Anulada", FillWeight = 12 });

            _estado = new EstadoListaControl();
            _estado.AccionSolicitada += async (s, e) =>
            {
                if (_estadoActual == EstadoLista.Error)
                    await CargarAsync();
                else
                {
                    _txtBuscar.Clear();
                    _paginacion.Reiniciar();
                    await CargarAsync();
                }
            };

            var pnlGrid = new Panel { Dock = DockStyle.Fill };
            pnlGrid.Controls.Add(_grid);
            pnlGrid.Controls.Add(_estado);

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            var pnlBottom = new Panel { Dock = DockStyle.Bottom, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Md), AutoSize = true };
            var pnlAnular = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };
            var lblMotivo = new Label { Text = Textos.Ventas.CampoMotivoAnulacion, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _txtMotivo = new TextBox { Width = 420, Height = UiTheme.Medidas.AlturaControl, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            _btnAnular = new Button
            {
                Text = Textos.Ventas.BotonAnularVenta,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Padding = new Padding(UiTheme.Espacio.Md + 2, 0, UiTheme.Espacio.Md + 2, 0),
                Height = UiTheme.Medidas.AlturaControl,
                BackColor = UiTheme.Error,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnAnular.FlatAppearance.BorderSize = 0;
            _btnAnular.Click += BtnAnular_Click;
            pnlAnular.Controls.AddRange(new Control[] { lblMotivo, _txtMotivo, _btnAnular });
            _lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 40 };
            pnlBottom.Controls.Add(_lblError);
            pnlBottom.Controls.Add(pnlAnular);

            Controls.Add(pnlGrid);
            Controls.Add(_paginacion);
            Controls.Add(pnlBottom);
            Controls.Add(pnlTop);

            Load += async (s, e) => await CargarAsync();
        }

        private async System.Threading.Tasks.Task CargarAsync()
        {
            try
            {
                var numeroFactura = string.IsNullOrWhiteSpace(_txtBuscar.Text) ? null : _txtBuscar.Text.Trim();
                var (ventas, total) = await VentaService.ListarAsync(numeroFactura, _chkSoloVigentes.Checked, _paginacion.Pagina, TamanoPagina);
                _paginacion.Actualizar(total, TamanoPagina);

                if (ventas.Count == 0)
                {
                    _grid.Visible = false;
                    _estadoActual = numeroFactura != null ? EstadoLista.VacioPorFiltro : EstadoLista.VacioInicial;
                    _estado.Mostrar(
                        _estadoActual,
                        _estadoActual == EstadoLista.VacioPorFiltro ? Textos.Ventas.SinResultadosBusqueda : Textos.Ventas.SinVentas,
                        _estadoActual == EstadoLista.VacioPorFiltro ? Textos.Comun.BotonLimpiarFiltros : null);
                    return;
                }

                _grid.DataSource = ventas;
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

        private async void BtnExportar_Click(object? sender, EventArgs e)
        {
            using var dialogo = new SaveFileDialog { Filter = Textos.Comun.FiltroExcel, FileName = "ventas.xlsx" };
            if (dialogo.ShowDialog(FindForm()) != DialogResult.OK) return;

            try
            {
                var numeroFactura = string.IsNullOrWhiteSpace(_txtBuscar.Text) ? null : _txtBuscar.Text.Trim();
                var filas = await VentaService.ExportarAExcelAsync(numeroFactura, _chkSoloVigentes.Checked, dialogo.FileName);
                MessageBox.Show(FindForm(), string.Format(Textos.Ventas.FormatoExportoOk, filas, dialogo.FileName), Textos.Ventas.TituloExportar);
            }
            catch (Exception ex)
            {
                MessageBox.Show(FindForm(), Textos.Ventas.NoSePudoExportarPrefijo + ex.Message, Sistemas.Core.UI.Textos.Comun.TituloError, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private async void BtnAnular_Click(object? sender, EventArgs e)
        {
            if (_grid.CurrentRow?.DataBoundItem is not VentaDto venta)
            {
                _lblError.Text = Textos.Ventas.ErrorSeleccioneVentaPrimero;
                return;
            }

            if (venta.Anulada)
            {
                _lblError.Text = Textos.Ventas.ErrorVentaYaAnulada;
                return;
            }

            var motivo = _txtMotivo.Text.Trim();
            if (motivo.Length == 0)
            {
                _lblError.Text = Textos.Ventas.ErrorIndiqueMotivoAnulacion;
                return;
            }

            if (MessageBox.Show(FindForm(), string.Format(Textos.Ventas.ConfirmarAnularFormato, venta.NumeroFactura, venta.Total),
                    Sistemas.Core.UI.Textos.Comun.TituloConfirmar, MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
                return;

            _btnAnular.Enabled = false;
            try
            {
                var (exito, mensaje) = await VentaService.AnularAsync(venta.Id, motivo, SessionContext.Current?.UsuarioId ?? 0);
                _lblError.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblError.Text = mensaje;
                if (exito)
                {
                    _txtMotivo.Clear();
                    await CargarAsync();
                }
            }
            catch (Exception ex)
            {
                _lblError.ForeColor = UiTheme.Error;
                _lblError.Text = Textos.Ventas.NoSeAnuloPrefijo + ex.Message;
            }
            finally
            {
                _btnAnular.Enabled = true;
            }
        }
    }
}
