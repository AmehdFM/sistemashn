using System;
using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI.Dashboard
{
    // Un renglón clickeable de la barra lateral: icono + texto. El texto se
    // oculta cuando la barra está colapsada, dejando solo el icono.
    internal sealed class SidebarItem : Panel
    {
        public IDashboardModule Modulo { get; }
        public event EventHandler? Seleccionado;

        private readonly Label _lblGlyph;
        private readonly Label _lblTexto;
        private bool _activo;

        public SidebarItem(IDashboardModule modulo)
        {
            Modulo = modulo;
            Height = 44;
            Dock = DockStyle.Top;
            Cursor = Cursors.Hand;
            BackColor = UiTheme.SidebarFondo;

            _lblGlyph = new Label
            {
                Text = modulo.Glyph,
                Font = UiTheme.FuenteGlyph,
                ForeColor = UiTheme.SidebarTexto,
                Size = new Size(48, 44),
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Left,
                Cursor = Cursors.Hand
            };

            _lblTexto = new Label
            {
                Text = modulo.Nombre,
                ForeColor = UiTheme.SidebarTexto,
                TextAlign = ContentAlignment.MiddleLeft,
                Dock = DockStyle.Fill,
                Cursor = Cursors.Hand
            };

            Controls.Add(_lblTexto);
            Controls.Add(_lblGlyph);

            foreach (Control c in new Control[] { this, _lblGlyph, _lblTexto })
            {
                c.Click += (s, e) => Seleccionado?.Invoke(this, EventArgs.Empty);
                c.MouseEnter += (s, e) => AplicarColor(hover: true);
                c.MouseLeave += (s, e) => AplicarColor(hover: false);
            }
        }

        public void MostrarTexto(bool mostrar) => _lblTexto.Visible = mostrar;

        public void MarcarActivo(bool activo)
        {
            _activo = activo;
            AplicarColor(hover: false);
        }

        private void AplicarColor(bool hover)
        {
            var color = _activo || hover ? UiTheme.SidebarFondoActivo : UiTheme.SidebarFondo;
            BackColor = color;
            _lblGlyph.BackColor = color;
            _lblTexto.BackColor = color;
        }
    }
}
