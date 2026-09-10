using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Controles;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Cuentas
{
    public sealed class CuentasPorCobrarPanel : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly int? _terceroId;
        private readonly CheckBox _chkSoloConSaldo;
        private readonly DataGridView _grid;
        private readonly EstadoListaControl _estado;
        private readonly PaginacionControl _paginacion;

        public CuentasPorCobrarPanel(int? terceroId = null)
        {
            _terceroId = terceroId;
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                BackColor = Color.White,
                Padding = new Padding(UiTheme.Espacio.Md)
            };
            var btnRegistrarPago = Botones.CrearToolbar(Textos.Cuentas.BotonRegistrarPago, primario: true);
            btnRegistrarPago.Click += BtnRegistrarPago_Click;
            _chkSoloConSaldo = new CheckBox { Text = Textos.Cuentas.CampoSoloConSaldo, AutoSize = true, Checked = true, Margin = new Padding(UiTheme.Espacio.Sm, UiTheme.Espacio.Sm + 2, 0, 0) };
            _chkSoloConSaldo.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            pnlToolbar.Controls.AddRange(new Control[] { btnRegistrarPago, _chkSoloConSaldo });

            _grid = new DataGridView { Visible = false };
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorCobrarDto.NumeroFactura), HeaderText = "Factura", FillWeight = 20 });
            var colMonto = new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorCobrarDto.MontoOriginal), HeaderText = "Monto original", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colMonto);
            _grid.Columns.Add(colMonto);
            var colSaldo = new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorCobrarDto.SaldoPendiente), HeaderText = "Saldo pendiente", FillWeight = 15 };
            GridStyler.ComoColumnaNumerica(colSaldo);
            _grid.Columns.Add(colSaldo);
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorCobrarDto.FechaVencimiento), HeaderText = "Vence", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorCobrarDto.Estado), HeaderText = "Estado", FillWeight = 15 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(CuentaPorCobrarDto.EstaVencida), HeaderText = "Vencida", FillWeight = 12 });
            _grid.CellFormatting += (s, e) =>
            {
                if (_grid.Rows[e.RowIndex].DataBoundItem is CuentaPorCobrarDto cuenta && cuenta.EstaVencida)
                    e.CellStyle!.BackColor = UiTheme.ErrorFondo;
            };

            _estado = new EstadoListaControl();
            _estado.AccionSolicitada += async (s, e) => await CargarAsync();

            var pnlGrid = new Panel { Dock = DockStyle.Fill };
            pnlGrid.Controls.Add(_grid);
            pnlGrid.Controls.Add(_estado);

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            Controls.Add(pnlGrid);
            Controls.Add(_paginacion);
            Controls.Add(pnlToolbar);

            Load += async (s, e) => await CargarAsync();
        }

        private async Task CargarAsync()
        {
            try
            {
                var (cuentas, total) = await CuentaPorCobrarService.ListarAsync(_chkSoloConSaldo.Checked, _paginacion.Pagina, TamanoPagina, _terceroId);
                _paginacion.Actualizar(total, TamanoPagina);

                if (cuentas.Count == 0)
                {
                    _grid.Visible = false;
                    _estado.Mostrar(EstadoLista.VacioInicial, Textos.Cuentas.SinCuentasPorCobrar);
                    return;
                }

                _grid.DataSource = cuentas;
                _grid.Visible = true;
                _estado.Ocultar();
            }
            catch (Exception ex)
            {
                _grid.Visible = false;
                _estado.Mostrar(EstadoLista.Error, Textos.Comun.NoSeConectoBdPrefijo + ex.Message, Textos.Comun.BotonReintentar);
            }
        }

        private async void BtnRegistrarPago_Click(object? sender, EventArgs e)
        {
            if (_grid.CurrentRow?.DataBoundItem is not CuentaPorCobrarDto cuenta)
            {
                MessageBox.Show(this, Textos.Cuentas.ErrorSeleccioneCuentaPrimero, Textos.Cuentas.TituloRegistrarPago);
                return;
            }

            if (cuenta.SaldoPendiente <= 0)
            {
                MessageBox.Show(this, Textos.Cuentas.ErrorCuentaSinSaldo, Textos.Cuentas.TituloRegistrarPago);
                return;
            }

            using var form = new FormRegistrarPago(cuenta.SaldoPendiente, (monto, metodo) =>
                CuentaPorCobrarService.RegistrarPagoAsync(cuenta.Id, monto, metodo, SessionContext.Current?.UsuarioId ?? 0));

            if (form.ShowDialog(FindForm()) == DialogResult.OK)
                await CargarAsync();
        }
    }
}
