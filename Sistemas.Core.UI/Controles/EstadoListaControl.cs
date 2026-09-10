using System;
using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI.Controles
{
    public enum EstadoLista
    {
        Cargando,
        VacioInicial,
        VacioPorFiltro,
        Error
    }

    // Los 4 estados obligatorios de toda lista (guía UI/UX §9.6): cargando,
    // vacío inicial (con acción para crear el primero), vacío por filtro
    // (mensaje distinto, con acción para limpiar filtros) y error (con
    // acción para reintentar). Reemplaza el "_lblEstado" de una sola línea
    // que cada pantalla de listado repetía a mano.
    public sealed class EstadoListaControl : UserControl
    {
        private readonly Label _lblMensaje;
        private readonly Button _btnAccion;

        public event EventHandler? AccionSolicitada;

        public EstadoListaControl()
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;
            Visible = false;

            _lblMensaje = new Label
            {
                AutoSize = false,
                Dock = DockStyle.Top,
                Height = 60,
                TextAlign = ContentAlignment.BottomCenter,
                Font = UiTheme.FuenteBase,
                ForeColor = UiTheme.TextoTenue,
                Padding = new Padding(UiTheme.Espacio.Xl, 0, UiTheme.Espacio.Xl, 0)
            };

            _btnAccion = Botones.CrearPrimario(string.Empty);
            _btnAccion.Dock = DockStyle.None;
            _btnAccion.Anchor = AnchorStyles.Top;
            _btnAccion.Margin = new Padding(0, UiTheme.Espacio.Md, 0, 0);
            _btnAccion.Click += (s, e) => AccionSolicitada?.Invoke(this, EventArgs.Empty);

            var pnlBoton = new Panel { Dock = DockStyle.Top, Height = 40 };
            pnlBoton.Resize += (s, e) => _btnAccion.Left = (pnlBoton.Width - _btnAccion.Width) / 2;
            pnlBoton.Controls.Add(_btnAccion);

            // Panel espaciador arriba para centrar verticalmente el bloque
            // mensaje+acción dentro del área disponible (guía: "espacio en
            // blanco intencional" para estados vacíos, Espacio.Huge).
            var pnlEspaciador = new Panel { Dock = DockStyle.Top, Height = UiTheme.Espacio.Huge * 2 };

            Controls.Add(pnlBoton);
            Controls.Add(_lblMensaje);
            Controls.Add(pnlEspaciador);
        }

        public void Mostrar(EstadoLista estado, string mensaje, string? textoAccion = null)
        {
            _lblMensaje.Text = mensaje;
            _lblMensaje.ForeColor = estado == EstadoLista.Error ? UiTheme.Error : UiTheme.TextoTenue;

            _btnAccion.Text = textoAccion ?? string.Empty;
            _btnAccion.Visible = !string.IsNullOrEmpty(textoAccion);
            if (_btnAccion.Visible && Parent != null)
                _btnAccion.Left = (Width - _btnAccion.Width) / 2;

            Visible = true;
        }

        public void Ocultar() => Visible = false;
    }
}
