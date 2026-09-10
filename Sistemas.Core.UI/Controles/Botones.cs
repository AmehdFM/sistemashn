using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI.Controles
{
    // Fábrica de botones estilizados compartida — reemplaza los helpers
    // "BotonToolbar" que cada pantalla definía por su cuenta (duplicados,
    // con firmas distintas, en InventarioControl.cs y ComprasControl.cs).
    public static class Botones
    {
        public static Button CrearPrimario(string texto)
        {
            var boton = CrearBase(texto);
            boton.BackColor = UiTheme.Primario;
            boton.ForeColor = Color.White;
            boton.FlatStyle = FlatStyle.Flat;
            boton.FlatAppearance.BorderSize = 0;
            return boton;
        }

        public static Button CrearSecundario(string texto) => CrearBase(texto);

        // Botón de barra de herramientas — primario opcional para la
        // única acción de acento por pantalla (guía UI/UX §6, regla 60/30/10).
        public static Button CrearToolbar(string texto, bool primario = false) =>
            primario ? CrearPrimario(texto) : CrearSecundario(texto);

        private static Button CrearBase(string texto) => new()
        {
            Text = texto,
            AutoSize = true,
            AutoSizeMode = AutoSizeMode.GrowAndShrink,
            Padding = new Padding(UiTheme.Espacio.Md + 2, 0, UiTheme.Espacio.Md + 2, 0),
            Height = UiTheme.Medidas.AlturaControl,
            Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0),
            Font = UiTheme.FuenteBase
        };
    }
}
