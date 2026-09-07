using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Cuentas
{
    public sealed class CuentasPorPagarPanel : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly int? _terceroId;
        private readonly CheckBox _chkSoloConSaldo;
        private readonly DataGridView _grid;
        private readonly PaginacionControl _paginacion;
        private readonly Label _lblEstado;

        public CuentasPorPagarPanel(int? terceroId = null)
        {
            _terceroId = terceroId;
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new Panel { Dock = DockStyle.Top, Height = 56, BackColor = Color.White };
            _chkSoloConSaldo = new CheckBox { Text = Textos.Cuentas.CampoSoloConSaldo, AutoSize = true, Location = new Point(12, 18), Checked = true };
            _chkSoloConSaldo.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            var btnRegistrarPago = new Button { Text = Textos.Cuentas.BotonRegistrarPago, Location = new Point(220, 12), Size = new Size(130, 32), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnRegistrarPago.FlatAppearance.BorderSize = 0;
            btnRegistrarPago.Click += BtnRegistrarPago_Click;
            pnlToolbar.Controls.AddRange(new Control[] { _chkSoloConSaldo, btnRegistrarPago });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorPagarDto.NumeroFacturaProveedor), HeaderText = "Factura proveedor", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorPagarDto.MontoOriginal), HeaderText = "Monto original", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorPagarDto.SaldoPendiente), HeaderText = "Saldo pendiente", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorPagarDto.FechaVencimiento), HeaderText = "Vence", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CuentaPorPagarDto.Estado), HeaderText = "Estado", FillWeight = 15 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(CuentaPorPagarDto.EstaVencida), HeaderText = "Vencida", FillWeight = 12 });
            _grid.CellFormatting += (s, e) =>
            {
                if (_grid.Rows[e.RowIndex].DataBoundItem is CuentaPorPagarDto cuenta && cuenta.EstaVencida)
                    e.CellStyle!.BackColor = UiTheme.ErrorFondo;
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
                var (cuentas, total) = await CuentaPorPagarService.ListarAsync(_chkSoloConSaldo.Checked, _paginacion.Pagina, TamanoPagina, _terceroId);
                _grid.DataSource = cuentas;
                _paginacion.Actualizar(total, TamanoPagina);
                _lblEstado.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblEstado.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private async void BtnRegistrarPago_Click(object? sender, EventArgs e)
        {
            if (_grid.CurrentRow?.DataBoundItem is not CuentaPorPagarDto cuenta)
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
                CuentaPorPagarService.RegistrarPagoAsync(cuenta.Id, monto, metodo, SessionContext.Current?.UsuarioId ?? 0));

            if (form.ShowDialog(FindForm()) == DialogResult.OK)
                await CargarAsync();
        }
    }
}
