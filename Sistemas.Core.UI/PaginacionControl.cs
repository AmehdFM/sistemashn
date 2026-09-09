using System;
using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI
{
    // Barra reutilizable de "< Anterior / Página X de Y / Siguiente >" para
    // cualquier pantalla de listado paginado (Inventario, Proveedores,
    // Compras, Ventas, Cuentas...), en cualquier vertical.
    //
    // Layout con TableLayoutPanel (Auto / Fill / Auto) en vez de posiciones
    // fijas: con coordenadas fijas, un texto largo en "Página X de Y" choca
    // contra el botón "Siguiente" y lo corta — el TableLayoutPanel reparte
    // el espacio sobrante siempre a la columna central, así el label nunca
    // invade a los botones sin importar el ancho de la ventana ni el largo
    // del texto.
    public sealed class PaginacionControl : UserControl
    {
        private readonly Button _btnAnterior;
        private readonly Button _btnSiguiente;
        private readonly Label _lblEstado;
        private int _totalPaginas = 1;

        public event EventHandler? PaginaCambiada;
        public int Pagina { get; private set; } = 1;

        public PaginacionControl()
        {
            Height = 40;
            Dock = DockStyle.Bottom;
            BackColor = Color.White;

            var tabla = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 3,
                RowCount = 1,
                Padding = new Padding(12, 6, 12, 6)
            };
            tabla.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            tabla.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f));
            tabla.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));

            _btnAnterior = new Button { Text = Textos.Comun.BotonAnterior, Size = new Size(100, 28), Anchor = AnchorStyles.Left };
            _btnAnterior.Click += (s, e) => { if (Pagina > 1) { Pagina--; PaginaCambiada?.Invoke(this, EventArgs.Empty); } };

            _lblEstado = new Label
            {
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleCenter,
                AutoEllipsis = true,
                ForeColor = UiTheme.TextoTenue
            };

            _btnSiguiente = new Button { Text = Textos.Comun.BotonSiguiente, Size = new Size(100, 28), Anchor = AnchorStyles.Right };
            _btnSiguiente.Click += (s, e) => { if (Pagina < _totalPaginas) { Pagina++; PaginaCambiada?.Invoke(this, EventArgs.Empty); } };

            tabla.Controls.Add(_btnAnterior, 0, 0);
            tabla.Controls.Add(_lblEstado, 1, 0);
            tabla.Controls.Add(_btnSiguiente, 2, 0);

            Controls.Add(tabla);
        }

        public void Actualizar(int totalFilas, int tamanoPagina)
        {
            _totalPaginas = Math.Max(1, (int)Math.Ceiling(totalFilas / (double)tamanoPagina));
            var seAjustoPagina = Pagina > _totalPaginas;
            if (seAjustoPagina) Pagina = _totalPaginas;

            _lblEstado.Text = string.Format(Textos.Comun.FormatoPaginacion, Pagina, _totalPaginas, totalFilas);
            _btnAnterior.Enabled = Pagina > 1;
            _btnSiguiente.Enabled = Pagina < _totalPaginas;

            // La página pedida ya no existe (el total bajó, p.ej. tras editar o
            // desactivar una fila) — el grid quedó lleno con la respuesta vacía
            // de la página vieja. Se dispara el mismo evento que el llamador ya
            // escucha para recargar con la página corregida.
            if (seAjustoPagina) PaginaCambiada?.Invoke(this, EventArgs.Empty);
        }

        public void Reiniciar() => Pagina = 1;
    }
}
