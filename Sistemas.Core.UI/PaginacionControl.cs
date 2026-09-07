using System;
using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI
{
    // Barra reutilizable de "< Anterior / Página X de Y / Siguiente >" para
    // cualquier pantalla de listado paginado (Inventario, Proveedores,
    // Compras, Ventas, Cuentas...), en cualquier vertical.
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

            // Location fijado aquí, antes de agregarse a ningún padre —ver
            // la nota en FormDashboardBase sobre por qué esto es necesario.
            _btnAnterior = new Button { Text = Textos.Comun.BotonAnterior, Size = new Size(100, 28), Location = new Point(12, 6) };
            _btnAnterior.Click += (s, e) => { if (Pagina > 1) { Pagina--; PaginaCambiada?.Invoke(this, EventArgs.Empty); } };

            _lblEstado = new Label
            {
                AutoSize = true,
                TextAlign = ContentAlignment.MiddleCenter,
                ForeColor = UiTheme.TextoTenue,
                Location = new Point(124, 12)
            };

            _btnSiguiente = new Button { Text = Textos.Comun.BotonSiguiente, Size = new Size(100, 28), Location = new Point(300, 6) };
            _btnSiguiente.Click += (s, e) => { if (Pagina < _totalPaginas) { Pagina++; PaginaCambiada?.Invoke(this, EventArgs.Empty); } };

            Controls.Add(_btnAnterior);
            Controls.Add(_lblEstado);
            Controls.Add(_btnSiguiente);
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
