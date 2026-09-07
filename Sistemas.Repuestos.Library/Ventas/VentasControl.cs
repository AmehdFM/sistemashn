using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Security;
using Sistemas.Core.UI;
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
        private readonly PaginacionControl _paginacion;
        private readonly TextBox _txtMotivo;
        private readonly Label _lblError;
        private readonly Button _btnAnular;

        public VentasControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 56, BackColor = Color.White };
            var lblBuscar = new Label { Text = Textos.Ventas.CampoNumeroFactura, AutoSize = true, Location = new Point(16, 4) };
            _txtBuscar = new TextBox { Location = new Point(16, 22), Size = new Size(260, 26) };
            _txtBuscar.KeyDown += async (s, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; _paginacion.Reiniciar(); await CargarAsync(); } };
            var btnBuscar = new Button { Text = Textos.Comun.BotonBuscar, Location = new Point(284, 21), Size = new Size(80, 28) };
            btnBuscar.Click += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            _chkSoloVigentes = new CheckBox { Text = Textos.Ventas.CampoSoloVigentes, AutoSize = true, Location = new Point(380, 25), Checked = true };
            _chkSoloVigentes.CheckedChanged += async (s, e) => { _paginacion.Reiniciar(); await CargarAsync(); };
            pnlTop.Controls.AddRange(new Control[] { lblBuscar, _txtBuscar, btnBuscar, _chkSoloVigentes });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.NumeroFactura), HeaderText = "N° factura", FillWeight = 25 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.Fecha), HeaderText = "Fecha", FillWeight = 18, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.Total), HeaderText = "Total", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(VentaDto.EsCredito), HeaderText = "Crédito", FillWeight = 12 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(VentaDto.MetodoPago), HeaderText = "Método de pago", FillWeight = 15 });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(VentaDto.Anulada), HeaderText = "Anulada", FillWeight = 12 });

            _paginacion = new PaginacionControl();
            _paginacion.PaginaCambiada += async (s, e) => await CargarAsync();

            var pnlBottom = new Panel { Dock = DockStyle.Bottom, Height = 108, BackColor = Color.White };
            var lblMotivo = new Label { Text = Textos.Ventas.CampoMotivoAnulacion, AutoSize = true, Location = new Point(16, 8) };
            _txtMotivo = new TextBox { Location = new Point(16, 28), Size = new Size(500, 26) };
            _btnAnular = new Button { Text = Textos.Ventas.BotonAnularVenta, Location = new Point(526, 27), Size = new Size(190, 28), BackColor = UiTheme.Error, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            _btnAnular.FlatAppearance.BorderSize = 0;
            _btnAnular.Click += BtnAnular_Click;
            _lblError = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(700, 40), Location = new Point(16, 62) };
            pnlBottom.Controls.AddRange(new Control[] { lblMotivo, _txtMotivo, _btnAnular, _lblError });

            Controls.Add(_grid);
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
                _grid.DataSource = ventas;
                _paginacion.Actualizar(total, TamanoPagina);
            }
            catch (Exception ex)
            {
                _lblError.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
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
