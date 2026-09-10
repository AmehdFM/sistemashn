using System.Drawing;
using System.Windows.Forms;

namespace Sistemas.Core.UI
{
    // Estilo común para los DataGridView de solo lectura usados en las
    // pantallas de listado — evita repetir el mismo bloque de propiedades
    // en cada pantalla de cada vertical.
    public static class GridStyler
    {
        public static void Aplicar(DataGridView grid)
        {
            grid.Dock = DockStyle.Fill;
            grid.ReadOnly = true;
            grid.AllowUserToAddRows = false;
            grid.AllowUserToDeleteRows = false;
            grid.AllowUserToResizeRows = false;
            grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            grid.MultiSelect = false;
            grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            grid.RowHeadersVisible = false;
            grid.BackgroundColor = Color.White;
            grid.BorderStyle = BorderStyle.None;
            grid.GridColor = UiTheme.Borde;
            grid.EnableHeadersVisualStyles = false;
            grid.ColumnHeadersDefaultCellStyle.BackColor = UiTheme.FondoContenido;
            grid.ColumnHeadersDefaultCellStyle.ForeColor = UiTheme.TextoOscuro;
            grid.ColumnHeadersDefaultCellStyle.Font = new Font(UiTheme.FuenteBase, FontStyle.Bold);
            // Selección: fondo sutil derivado del acento, nunca texto
            // blanco sobre un color sólido (anti-patrón de la guía UI/UX).
            grid.DefaultCellStyle.SelectionBackColor = UiTheme.SeleccionFila;
            grid.DefaultCellStyle.SelectionForeColor = UiTheme.TextoOscuro;
            grid.DefaultCellStyle.Font = UiTheme.FuenteBase;
            grid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing;
            grid.ColumnHeadersHeight = UiTheme.Medidas.AlturaEncabezadoFila;
            grid.RowTemplate.Height = UiTheme.Medidas.AlturaFila;
            grid.CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal;
        }

        // Aplica alineación a la derecha + formato N2 a una columna de
        // dinero/cantidad — mismo criterio en toda pantalla con montos
        // (guía UI/UX §9.1: números siempre a la derecha, texto a la
        // izquierda).
        public static void ComoColumnaNumerica(DataGridViewColumn columna, string formato = "N2")
        {
            columna.DefaultCellStyle.Format = formato;
            columna.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleRight;
            columna.HeaderCell.Style.Alignment = DataGridViewContentAlignment.MiddleRight;
        }
    }
}
