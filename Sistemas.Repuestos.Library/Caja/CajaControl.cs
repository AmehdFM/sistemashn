using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Caja
{
    // Módulo "Caja": arriba, el estado de la sesión actual (abierta o
    // cerrada) con el botón correspondiente; abajo, el historial paginado —
    // mismo esqueleto que Ventas/VentasControl.cs.
    public sealed class CajaControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly Label _lblEstado;
        private readonly Button _btnAbrirCaja;
        private readonly Button _btnCerrarCaja;
        private readonly Label _lblError;

        private readonly DataGridView _grid;
        private readonly EstadoListaControl _estadoLista;
        private readonly PaginacionControl _paginacion;

        private SesionCajaDto? _sesionAbierta;

        public CajaControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlEstado = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };
            _lblEstado = new Label { Dock = DockStyle.Top, Height = 24, Font = new Font(UiTheme.FuenteBase, FontStyle.Bold), Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var pnlAcciones = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            _btnAbrirCaja = Botones.CrearPrimario(Textos.Caja.BotonAbrirCaja);
            _btnAbrirCaja.Visible = false;
            _btnAbrirCaja.Click += BtnAbrirCaja_Click;
            _btnCerrarCaja = new Button
            {
                Text = Textos.Caja.BotonCerrarCaja,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Padding = new Padding(UiTheme.Espacio.Md + 2, 0, UiTheme.Espacio.Md + 2, 0),
                Height = UiTheme.Medidas.AlturaControl,
                BackColor = UiTheme.Error,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Visible = false
            };
            _btnCerrarCaja.FlatAppearance.BorderSize = 0;
            _btnCerrarCaja.Click += BtnCerrarCaja_Click;
            pnlAcciones.Controls.AddRange(new Control[] { _btnAbrirCaja, _btnCerrarCaja });

            _lblError = new Label { ForeColor = UiTheme.Error, Dock = DockStyle.Top, Height = 24, Margin = new Padding(0, UiTheme.Espacio.Sm, 0, 0) };

            pnlEstado.Controls.Add(_lblError);
            pnlEstado.Controls.Add(pnlAcciones);
            pnlEstado.Controls.Add(_lblEstado);

            _grid = new DataGridView { Visible = false };
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.Id), HeaderText = "N°", FillWeight = 8 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.FechaApertura), HeaderText = "Apertura", FillWeight = 18, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            var colMontoApertura = new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.MontoApertura), HeaderText = "Monto apertura", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colMontoApertura);
            _grid.Columns.Add(colMontoApertura);
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.FechaCierre), HeaderText = "Cierre", FillWeight = 18, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            var colContado = new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.MontoCierreDeclarado), HeaderText = "Contado", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colContado);
            _grid.Columns.Add(colContado);
            var colEsperado = new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.MontoCierreCalculado), HeaderText = "Esperado", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colEsperado);
            _grid.Columns.Add(colEsperado);
            var colDiferencia = new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.Diferencia), HeaderText = "Diferencia", FillWeight = 12 };
            GridStyler.ComoColumnaNumerica(colDiferencia);
            _grid.Columns.Add(colDiferencia);
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.Estado), HeaderText = "Estado", FillWeight = 10 });

            _estadoLista = new EstadoListaControl();
            _estadoLista.AccionSolicitada += async (s, e) => await CargarHistorialAsync();

            var pnlGrid = new Panel { Dock = DockStyle.Fill };
            pnlGrid.Controls.Add(_grid);
            pnlGrid.Controls.Add(_estadoLista);

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarHistorialAsync();

            Controls.Add(pnlGrid);
            Controls.Add(_paginacion);
            Controls.Add(pnlEstado);

            Load += async (s, e) => await RecargarTodoAsync();
        }

        private async System.Threading.Tasks.Task RecargarTodoAsync()
        {
            await CargarEstadoAsync();
            await CargarHistorialAsync();
        }

        private async System.Threading.Tasks.Task CargarEstadoAsync()
        {
            try
            {
                _sesionAbierta = await CajaService.ObtenerAbiertaAsync();
                if (_sesionAbierta != null)
                {
                    var quien = _sesionAbierta.UsuarioAperturaNombre ?? string.Format(Textos.Caja.UsuarioGenericoFormato, _sesionAbierta.UsuarioAperturaId);
                    _lblEstado.Text = string.Format(Textos.Caja.EstadoAbiertaFormato, quien, _sesionAbierta.FechaApertura, _sesionAbierta.MontoApertura);
                    _btnAbrirCaja.Visible = false;
                    _btnCerrarCaja.Visible = true;
                }
                else
                {
                    _lblEstado.Text = Textos.Caja.EstadoCerrada;
                    _btnAbrirCaja.Visible = true;
                    _btnCerrarCaja.Visible = false;
                }
                _lblError.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private async System.Threading.Tasks.Task CargarHistorialAsync()
        {
            try
            {
                var (sesiones, total) = await CajaService.ListarAsync(_paginacion.Pagina, TamanoPagina);
                _paginacion.Actualizar(total, TamanoPagina);

                if (sesiones.Count == 0)
                {
                    _grid.Visible = false;
                    _estadoLista.Mostrar(EstadoLista.VacioInicial, Textos.Caja.SinHistorial);
                    return;
                }

                _grid.DataSource = sesiones;
                _grid.Visible = true;
                _estadoLista.Ocultar();
            }
            catch (Exception ex)
            {
                _grid.Visible = false;
                _estadoLista.Mostrar(EstadoLista.Error, Textos.Comun.NoSeConectoBdPrefijo + ex.Message, Textos.Comun.BotonReintentar);
            }
        }

        private async void BtnAbrirCaja_Click(object? sender, EventArgs e)
        {
            using var form = new FormAbrirCaja();
            if (form.ShowDialog(FindForm()) == DialogResult.OK)
            {
                _paginacion.Reiniciar();
                await RecargarTodoAsync();
            }
        }

        private async void BtnCerrarCaja_Click(object? sender, EventArgs e)
        {
            if (_sesionAbierta == null) return;

            using var form = new FormCerrarCaja(_sesionAbierta.Id);
            if (form.ShowDialog(FindForm()) == DialogResult.OK)
            {
                _paginacion.Reiniciar();
                await RecargarTodoAsync();
            }
        }
    }
}
