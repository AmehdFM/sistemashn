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
            grid.DefaultCellStyle.SelectionBackColor = UiTheme.Primario;
            grid.DefaultCellStyle.SelectionForeColor = Color.White;
            grid.DefaultCellStyle.Font = UiTheme.FuenteBase;
            grid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.AutoSize;
        }
    }
}
