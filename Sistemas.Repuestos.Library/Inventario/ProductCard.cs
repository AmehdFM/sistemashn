using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.UI;

namespace Sistemas.Repuestos.Library.Inventario
{
    // Una tarjeta de producto para la grilla de Inventario: solo lo esencial
    // para decidir de un vistazo (Nombre, Categoría, Stock) — el resto de los
    // datos (Precio, ISV, Stock mínimo, Unidad, Activo) se ve al abrir el
    // detalle (ProductDetailControl), que reemplaza a esta grilla en el
    // mismo lugar. Un clic navega directo al detalle — no hay estado de
    // selección persistente, solo un resalte al pasar el mouse.
    public sealed class ProductCard : UserControl
    {
        private bool _resaltada;

        public ProductoDto Producto { get; }

        public ProductCard(ProductoDto producto)
        {
            Producto = producto;
            Size = new Size(240, 100);
            Margin = new Padding(8);
            BackColor = Color.White;
            Cursor = Cursors.Hand;

            var lblNombre = new Label
            {
                Text = producto.Nombre,
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                ForeColor = producto.Activo ? UiTheme.TextoOscuro : UiTheme.TextoTenue,
                AutoEllipsis = true,
                Location = new Point(12, 10),
                Size = new Size(216, 20),
                Cursor = Cursors.Hand
            };

            var lblCategoria = new Label
            {
                Text = producto.NombreCategoria ?? Textos.Inventario.SinCategoria,
                ForeColor = UiTheme.TextoTenue,
                AutoEllipsis = true,
                Location = new Point(12, 32),
                Size = new Size(216, 18),
                Cursor = Cursors.Hand
            };

            var bajoMinimo = producto.StockActual < producto.StockMinimo;
            var lblStock = new Label
            {
                Text = string.Format(Textos.Inventario.CardStockFormato,
                    CantidadFormatter.FormatearCantidad(producto.StockActual, producto.PermiteFraccionUnidad),
                    producto.UnidadMedidaSimbolo).Trim(),
                Font = new Font(UiTheme.FuenteBase, FontStyle.Bold),
                ForeColor = bajoMinimo ? UiTheme.Error : (producto.Activo ? UiTheme.Primario : UiTheme.TextoTenue),
                AutoEllipsis = true,
                Location = new Point(12, 62),
                Size = new Size(160, 22),
                Cursor = Cursors.Hand
            };

            Controls.Add(lblNombre);
            Controls.Add(lblCategoria);
            Controls.Add(lblStock);

            if (!producto.Activo)
            {
                var lblInactivo = new Label
                {
                    Text = Textos.Inventario.CardEtiquetaInactivo,
                    Font = new Font(UiTheme.FuenteBase.FontFamily, 8f, FontStyle.Italic),
                    ForeColor = UiTheme.TextoTenue,
                    AutoSize = true,
                    Location = new Point(172, 66),
                    Cursor = Cursors.Hand
                };
                Controls.Add(lblInactivo);
                PropagarClicks(lblInactivo);
            }

            PropagarClicks(this);
            PropagarClicks(lblNombre);
            PropagarClicks(lblCategoria);
            PropagarClicks(lblStock);

            MouseEnter += (s, e) => CambiarResalte(true);
            MouseLeave += (s, e) => CambiarResalte(false);
        }

        private void CambiarResalte(bool resaltada)
        {
            if (_resaltada == resaltada) return;
            _resaltada = resaltada;
            Invalidate();
        }

        // Los clics sobre los Label hijos no burbujean solos hacia el
        // UserControl contenedor — se reenvían explícitamente para que
        // InventarioControl pueda escuchar un solo Click en la tarjeta sin
        // que importe sobre qué parte exacta cayó el clic. MouseEnter/Leave
        // de un Label hijo tampoco burbujean, así que el resalte también se
        // engancha ahí para que cubra toda la tarjeta, no solo el fondo.
        private void PropagarClicks(Control control)
        {
            control.Click += (s, e) => OnClick(e);
            if (control != this)
            {
                control.MouseEnter += (s, e) => CambiarResalte(true);
                control.MouseLeave += (s, e) => CambiarResalte(false);
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            var color = _resaltada ? UiTheme.Primario : UiTheme.Borde;
            var ancho = _resaltada ? 2 : 1;
            using var pen = new Pen(color, ancho);
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            e.Graphics.DrawRectangle(pen, rect);
        }
    }
}
