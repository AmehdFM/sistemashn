using System.Windows.Forms;

namespace Sistemas.Core.UI
{
    // Todas las cantidades se guardan igual (DECIMAL(12,2)); lo único que
    // cambia según la unidad de medida del producto es si se admite
    // fracción o no. Un solo lugar para esa lógica evita repetirla en cada
    // pantalla que captura o muestra una cantidad.
    public static class CantidadFormatter
    {
        public static void AplicarModoCantidad(NumericUpDown control, bool permiteFraccion)
        {
            control.DecimalPlaces = permiteFraccion ? 2 : 0;
            control.Increment = permiteFraccion ? 0.01m : 1m;
        }

        public static string FormatearCantidad(decimal cantidad, bool permiteFraccion) =>
            cantidad.ToString(permiteFraccion ? "N2" : "N0");
    }
}
