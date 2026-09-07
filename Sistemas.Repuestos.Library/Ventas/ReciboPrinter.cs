using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Printing;
using System.Windows.Forms;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Ventas
{
    // Recibo de texto plano tamaño carta a la impresora predeterminada de
    // Windows — sin diseño térmico todavía, eso queda como mejora futura.
    public static class ReciboPrinter
    {
        public static void Imprimir(string nombreNegocio, string numeroFactura, DateTime fecha, decimal total, IReadOnlyList<LineaCarritoDto> lineas,
            decimal? efectivoRecibido = null, decimal? vuelto = null)
        {
            var documento = new PrintDocument();
            documento.PrintPage += (s, e) => DibujarPagina(e, nombreNegocio, numeroFactura, fecha, total, lineas, efectivoRecibido, vuelto);

            using var dialogo = new PrintDialog { Document = documento };
            if (dialogo.ShowDialog() == DialogResult.OK)
                documento.Print();
        }

        private static void DibujarPagina(PrintPageEventArgs e, string nombreNegocio, string numeroFactura, DateTime fecha, decimal total, IReadOnlyList<LineaCarritoDto> lineas,
            decimal? efectivoRecibido, decimal? vuelto)
        {
            var g = e.Graphics!;
            var fuente = new Font("Consolas", 10f);
            var fuenteTitulo = new Font("Consolas", 12f, FontStyle.Bold);
            float x = e.MarginBounds.Left;
            float y = e.MarginBounds.Top;
            float alturaLinea = fuente.GetHeight(g) + 2;

            void Escribir(string texto, Font? f = null)
            {
                g.DrawString(texto, f ?? fuente, Brushes.Black, x, y);
                y += alturaLinea;
            }

            Escribir(string.Format(Textos.Pos.ReciboEncabezadoFormato, nombreNegocio), fuenteTitulo);
            Escribir(string.Format(Textos.Pos.ReciboFacturaFormato, numeroFactura));
            Escribir(string.Format(Textos.Pos.ReciboFechaFormato, fecha));
            Escribir(new string('-', 60));
            Escribir(string.Format("{0,-28}{1,6}{2,12}{3,12}", Textos.Pos.ReciboColumnaProducto, Textos.Pos.ReciboColumnaCantidad, Textos.Pos.ReciboColumnaPrecioUnitario, Textos.Pos.ReciboColumnaSubtotal));
            foreach (var linea in lineas)
                Escribir(string.Format("{0,-28}{1,6}{2,12:N2}{3,12:N2}", Truncar(linea.Nombre, 28), linea.Cantidad, linea.PrecioUnitarioReferencial, linea.SubtotalReferencial));
            Escribir(new string('-', 60));
            Escribir(string.Format(Textos.Pos.ReciboTotalFormato, total), fuenteTitulo);

            if (efectivoRecibido.HasValue && vuelto.HasValue)
            {
                Escribir(string.Format(Textos.Pos.ReciboEfectivoRecibidoFormato, efectivoRecibido.Value));
                Escribir(string.Format(Textos.Pos.ReciboVueltoFormato, vuelto.Value));
            }
        }

        private static string Truncar(string texto, int longitud) =>
            texto.Length <= longitud ? texto : texto.Substring(0, longitud - 1) + "…";
    }
}
