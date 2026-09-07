using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI.Dashboard
{
    // Pantalla "Menú": un botón grande (icono + texto) por cada módulo
    // disponible, clickeable para navegar entre pantallas.
    public sealed class ModuleLauncherControl : UserControl
    {
        public event EventHandler<IDashboardModule>? ModuloSeleccionado;

        public ModuleLauncherControl(IReadOnlyList<IDashboardModule> modulos)
        {
            Dock = DockStyle.Fill;
            BackColor = UiTheme.FondoContenido;

            var flow = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(32),
                AutoScroll = true
            };

            foreach (var modulo in modulos)
            {
                flow.Controls.Add(CrearBoton(modulo));
            }

            Controls.Add(flow);
        }

        private Control CrearBoton(IDashboardModule modulo)
        {
            var boton = new Panel
            {
                Size = new Size(160, 120),
                Margin = new Padding(12),
                BackColor = Color.White,
                Cursor = Cursors.Hand,
                BorderStyle = BorderStyle.FixedSingle
            };

            var lblGlyph = new Label
            {
                Text = modulo.Glyph,
                Font = new Font(UiTheme.FuenteGlyph.FontFamily, 28f),
                ForeColor = UiTheme.Primario,
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Top,
                Height = 76,
                Cursor = Cursors.Hand
            };

            var lblTexto = new Label
            {
                Text = modulo.Nombre,
                ForeColor = UiTheme.TextoOscuro,
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Fill,
                Cursor = Cursors.Hand
            };

            boton.Controls.Add(lblTexto);
            boton.Controls.Add(lblGlyph);

            foreach (Control c in new Control[] { boton, lblGlyph, lblTexto })
                c.Click += (s, e) => ModuloSeleccionado?.Invoke(this, modulo);

            return boton;
        }
    }
}
