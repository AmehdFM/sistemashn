using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Repuestos.Library.Models;
using Sistemas.Repuestos.Library.Services;

namespace Sistemas.Repuestos.Library.Compras
{
    public sealed class ComprasControl : UserControl
    {
        private const int TamanoPagina = 50;

        private readonly DataGridView _grid;
        private readonly PaginacionControl _paginacion;
        private readonly Label _lblEstado;

        public ComprasControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var pnlToolbar = new Panel { Dock = DockStyle.Top, Height = 56, BackColor = Color.White };
            var btnNuevaCompra = new Button { Text = Textos.Compras.BotonNuevaCompra, Location = new Point(12, 12), Size = new Size(140, 32), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnNuevaCompra.FlatAppearance.BorderSize = 0;
            btnNuevaCompra.Click += BtnNuevaCompra_Click;
            var btnActualizar = new Button { Text = Textos.Compras.BotonActualizar, Location = new Point(160, 12), Size = new Size(100, 32) };
            btnActualizar.Click += async (s, e) => await CargarAsync();
            pnlToolbar.Controls.AddRange(new Control[] { btnNuevaCompra, btnActualizar });

            _grid = new DataGridView();
            GridStyler.Aplicar(_grid);
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.Fecha), HeaderText = "Fecha", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "dd/MM/yyyy HH:mm" } });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.NombreProveedor), HeaderText = "Proveedor", FillWeight = 25 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.NumeroFacturaProveedor), HeaderText = "N° factura proveedor", FillWeight = 20 });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(CompraDto.Total), HeaderText = "Total", FillWeight = 15, DefaultCellStyle = new DataGridViewCellStyle { Format = "N2", Alignment = DataGridViewContentAlignment.MiddleRight } });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(CompraDto.EsCredito), HeaderText = "Crédito", FillWeight = 10 });

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
                var (compras, total) = await CompraService.ListarAsync(null, _paginacion.Pagina, TamanoPagina);
                _grid.DataSource = compras;
                _paginacion.Actualizar(total, TamanoPagina);
                _lblEstado.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblEstado.Text = Textos.Comun.NoSeConectoBdPrefijo + ex.Message;
            }
        }

        private async void BtnNuevaCompra_Click(object? sender, EventArgs e)
        {
            using var form = new FormRegistrarCompra();
            form.ShowDialog(FindForm());
            _paginacion.Reiniciar();
            await CargarAsync();
        }
    }
}
