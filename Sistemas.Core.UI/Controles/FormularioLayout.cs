using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI.Controles
{
    // Reemplazo de "new Point(x, y)" en pantallas de formulario: arma una
    // grilla de 2 columnas (etiqueta + control) con la separación estándar
    // de la guía UI/UX (Espacio.Lg entre filas), en vez de posicionar cada
    // control a mano. Etiquetas a la izquierda, alineadas a la derecha y
    // pegadas al campo — mismo patrón que ya usaban las pantallas antes de
    // esta migración, solo que ahora fluye con el ancho disponible.
    public static class FormularioLayout
    {
        public static TableLayoutPanel CrearGrilla(int anchoEtiqueta = 140)
        {
            var grilla = new TableLayoutPanel
            {
                ColumnCount = 2,
                RowCount = 0,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Dock = DockStyle.Top,
                Padding = new Padding(0)
            };
            grilla.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, anchoEtiqueta));
            grilla.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            return grilla;
        }

        // Agrega una fila etiqueta+control. El control pasa a mandar su
        // propio Height/Width (ej. NumericUpDown.Width=100) — esta grilla
        // solo controla la posición, no el tamaño del control en sí.
        public static void AgregarCampo(TableLayoutPanel grilla, string etiqueta, Control control)
        {
            var fila = grilla.RowCount;
            grilla.RowCount = fila + 1;
            grilla.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            var lbl = new Label
            {
                Text = etiqueta,
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleRight,
                Padding = new Padding(0, 0, UiTheme.Espacio.Sm, 0),
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg),
                ForeColor = UiTheme.TextoTenue,
                Font = UiTheme.FuenteBase
            };
            control.Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg);
            control.Anchor = AnchorStyles.Left | AnchorStyles.Top;

            grilla.Controls.Add(lbl, 0, fila);
            grilla.Controls.Add(control, 1, fila);
        }

        // Fila donde el control ocupa el ancho completo (sin etiqueta a la
        // izquierda) — para descripciones/observaciones multilinea.
        public static void AgregarCampoAncho(TableLayoutPanel grilla, Control control)
        {
            var fila = grilla.RowCount;
            grilla.RowCount = fila + 1;
            grilla.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            control.Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg);
            control.Dock = DockStyle.Fill;

            grilla.Controls.Add(control, 0, fila);
            grilla.SetColumnSpan(control, 2);
        }
    }
}
