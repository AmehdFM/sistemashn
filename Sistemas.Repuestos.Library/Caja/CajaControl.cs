using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.UI;
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

        private readonly Panel _pnlEstado;
        private readonly Label _lblEstado;
        private readonly Button _btnAbrirCaja;
        private readonly Button _btnCerrarCaja;
        private readonly Label _lblError;

        private readonly DataGridView _grid;
        private readonly PaginacionControl _paginacion;

        private SesionCajaDto? _sesionAbierta;

        public CajaControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            _pnlEstado = new Panel { Dock = DockStyle.Top, Height = 72, BackColor = Color.White };
            _lblEstado = new Label { AutoSize = false, Location = new Point(16, 8), Size = new Size(700, 22), Font = new Font(UiTheme.FuenteBase, FontStyle.Bold) };
            _btnAbrirCaja = new Button { Text = Textos.Caja.BotonAbrirCaja, Location = new Point(16, 34), Size = new Size(140, 28), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Visible = false };
            _btnAbrirCaja.FlatAppearance.BorderSize = 0;
            _btnAbrirCaja.Click += BtnAbrirCaja_Click;
            _btnCerrarCaja = new Button { Text = Textos.Caja.BotonCerrarCaja, Location = new Point(16, 34), Size = new Size(140, 28), BackColor = UiTheme.Error, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Visible = false };
            _btnCerrarCaja.FlatAppearance.BorderSize = 0;
            _btnCerrarCaja.Click += BtnCerrarCaja_Click;
            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = true, Location = new Point(170, 40) };
            _pnlEstado.Controls.AddRange(new Control[] { _lblEstado, _btnAbrirCaja, _btnCerrarCaja, _lblError });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.Id), HeaderText = "N°", FillWeight = 8 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.FechaApertura), HeaderText = "Apertura", FillWeight = 18, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.MontoApertura), HeaderText = "Monto apertura", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.FechaCierre), HeaderText = "Cierre", FillWeight = 18, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.MontoCierreDeclarado), HeaderText = "Contado", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.MontoCierreCalculado), HeaderText = "Esperado", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.Diferencia), HeaderText = "Diferencia", FillWeight = 12, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(SesionCajaDto.Estado), HeaderText = "Estado", FillWeight = 10 });

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarHistorialAsync();

            Controls.Add(_grid);
            Controls.Add(_paginacion);
            Controls.Add(_pnlEstado);

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
                _grid.DataSource = sesiones;
                _paginacion.Actualizar(total, TamanoPagina);
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
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
