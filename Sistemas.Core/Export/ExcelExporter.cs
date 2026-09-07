using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using ClosedXML.Excel;

namespace Sistemas.Core.Export
{
    // Helper genérico y reutilizable de lectura/escritura de Excel — no sabe
    // nada de productos ni de ningún dominio en particular; eso lo resuelve
    // quien lo consuma (ej. Inventory/ProductService.cs).
    public static class ExcelExporter
    {
        public static void Exportar(string rutaArchivo, string[] encabezados, IEnumerable<object?[]> filas)
        {
            using var libro = new XLWorkbook();
            var hoja = libro.Worksheets.Add("Datos");

            for (int c = 0; c < encabezados.Length; c++)
                hoja.Cell(1, c + 1).Value = encabezados[c];
            hoja.Row(1).Style.Font.Bold = true;

            int fila = 2;
            foreach (var valores in filas)
            {
                for (int c = 0; c < valores.Length; c++)
                    EscribirCelda(hoja.Cell(fila, c + 1), valores[c]);
                fila++;
            }

            hoja.Columns().AdjustToContents();
            libro.SaveAs(rutaArchivo);
        }

        public static void GenerarPlantilla(string rutaArchivo, string[] encabezados) =>
            Exportar(rutaArchivo, encabezados, Enumerable.Empty<object?[]>());

        // Compara la fila de encabezados contra los esperados (mismo orden,
        // mismo texto) ANTES de leer ninguna fila de datos — si no coincide,
        // devuelve un error claro en vez de intentar interpretar columnas
        // equivocadas.
        public static (bool CoincideEstructura, string? Error, List<string?[]> Filas) LeerHoja(
            string rutaArchivo, string[] encabezadosEsperados)
        {
            using var libro = new XLWorkbook(rutaArchivo);
            var hoja = libro.Worksheets.First();

            for (int c = 0; c < encabezadosEsperados.Length; c++)
            {
                var real = hoja.Cell(1, c + 1).GetString().Trim();
                var esperado = encabezadosEsperados[c];
                if (!string.Equals(real, esperado, StringComparison.OrdinalIgnoreCase))
                {
                    var mensaje = string.Format(Textos.Excel.ColumnaNoCoincideFormato, c + 1, esperado, real);
                    return (false, mensaje, new List<string?[]>());
                }
            }

            // Se recorre hasta la última fila realmente usada en la hoja, no
            // hasta la primera fila vacía: una fila en blanco en medio de los
            // datos (frecuente por error humano al preparar el Excel) no debe
            // truncar silenciosamente el resto de las filas.
            var filas = new List<string?[]>();
            var ultimaFila = hoja.LastRowUsed()?.RowNumber() ?? 1;
            for (var filaActual = 2; filaActual <= ultimaFila; filaActual++)
            {
                if (hoja.Row(filaActual).IsEmpty()) continue;

                var valores = new string?[encabezadosEsperados.Length];
                for (int c = 0; c < encabezadosEsperados.Length; c++)
                {
                    var texto = hoja.Cell(filaActual, c + 1).GetString().Trim();
                    valores[c] = texto.Length == 0 ? null : texto;
                }
                filas.Add(valores);
            }

            return (true, null, filas);
        }

        private static void EscribirCelda(IXLCell celda, object? valor)
        {
            switch (valor)
            {
                case null: break;
                case string s: celda.Value = s; break;
                case int i: celda.Value = i; break;
                case decimal d: celda.Value = d; break;
                case double db: celda.Value = db; break;
                case DateTime dt: celda.Value = dt; break;
                case bool b: celda.Value = b; break;
                default: celda.Value = valor.ToString(); break;
            }
        }
    }
}
