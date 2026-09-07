using System;
using System.Collections.Generic;
using System.Data;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Export;
using Sistemas.Core.Inventory.Models;

namespace Sistemas.Core.Inventory
{
    public static class ProductService
    {
        // Columnas exactas de la plantilla de importación (por nombre de
        // categoría, no por Id — más fácil de llenar para quien prepara el
        // Excel). El mismo arreglo se usa para validar la estructura del
        // archivo y para generar la plantilla en blanco.
        public static readonly string[] EncabezadosImportacion =
            { "Codigo", "Nombre", "Descripcion", "PrecioUnitario", "Categoria", "TasaISV", "StockMinimo" };

        public static async Task<(List<ProductoDto> Productos, int TotalFilas)> ListarAsync(
            bool soloActivos, int? categoriaId, string? busqueda, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Inventario.sp_ListarProductos",
                new { SoloActivos = soloActivos, CategoriaId = categoriaId, Busqueda = busqueda, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var productos = (await multi.ReadAsync<ProductoDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (productos, total);
        }

        public static async Task<(bool Exito, string Mensaje, int? ProductoId)> CrearAsync(
            string codigo, string nombre, string? descripcion, decimal precioUnitario,
            int? categoriaId, decimal tasaIsv, int stockMinimo, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? ProductoId)>(
                "Inventario.sp_CrearProducto",
                new
                {
                    Codigo = codigo,
                    Nombre = nombre,
                    Descripcion = descripcion,
                    PrecioUnitario = precioUnitario,
                    CategoriaId = categoriaId,
                    TasaISV = tasaIsv,
                    StockMinimo = stockMinimo,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje)> ActualizarAsync(
            int productoId, string nombre, string? descripcion, decimal precioUnitario,
            int? categoriaId, decimal tasaIsv, int stockMinimo, bool activo, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Inventario.sp_ActualizarProducto",
                new
                {
                    ProductoId = productoId,
                    Nombre = nombre,
                    Descripcion = descripcion,
                    PrecioUnitario = precioUnitario,
                    CategoriaId = categoriaId,
                    TasaISV = tasaIsv,
                    StockMinimo = stockMinimo,
                    Activo = activo,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<ResultadoImportacionDto> ImportarDesdeExcelAsync(string rutaArchivo, int usuarioId)
        {
            var (coincide, error, filas) = ExcelExporter.LeerHoja(rutaArchivo, EncabezadosImportacion);
            if (!coincide)
            {
                return new ResultadoImportacionDto { Exito = false, Mensaje = error ?? "El archivo no tiene la estructura esperada" };
            }

            var tabla = new DataTable();
            tabla.Columns.Add("Codigo", typeof(string));
            tabla.Columns.Add("Nombre", typeof(string));
            tabla.Columns.Add("Descripcion", typeof(string));
            tabla.Columns.Add("PrecioUnitario", typeof(decimal));
            tabla.Columns.Add("CategoriaId", typeof(int));
            tabla.Columns.Add("TasaISV", typeof(decimal));
            tabla.Columns.Add("StockMinimo", typeof(int));

            var erroresPrevios = new List<DetalleImportacionDto>();

            foreach (var fila in filas)
            {
                var codigo = fila[0] ?? string.Empty;
                if (string.IsNullOrWhiteSpace(codigo))
                {
                    erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "Código vacío" });
                    continue;
                }

                if (string.IsNullOrWhiteSpace(fila[1]))
                {
                    erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "Nombre vacío" });
                    continue;
                }

                if (!decimal.TryParse(fila[3], NumberStyles.Any, CultureInfo.InvariantCulture, out var precio) || precio < 0)
                {
                    erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "Precio unitario inválido" });
                    continue;
                }

                int? categoriaId = null;
                if (!string.IsNullOrWhiteSpace(fila[4]))
                {
                    var (exitoCat, mensajeCat, idCat) = await CategoryService.ObtenerOCrearPorNombreAsync(fila[4]!, usuarioId);
                    if (!exitoCat)
                    {
                        erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "No se pudo resolver la categoría: " + mensajeCat });
                        continue;
                    }
                    categoriaId = idCat;
                }

                decimal? tasaIsv = null;
                if (!string.IsNullOrWhiteSpace(fila[5]))
                {
                    if (!decimal.TryParse(fila[5], NumberStyles.Any, CultureInfo.InvariantCulture, out var tasa) || (tasa != 0 && tasa != 15 && tasa != 18))
                    {
                        erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "Tasa de ISV inválida (debe ser 0, 15 o 18)" });
                        continue;
                    }
                    tasaIsv = tasa;
                }

                int? stockMinimo = null;
                if (!string.IsNullOrWhiteSpace(fila[6]))
                {
                    if (!int.TryParse(fila[6], out var stock) || stock < 0)
                    {
                        erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "Stock mínimo inválido" });
                        continue;
                    }
                    stockMinimo = stock;
                }

                var renglon = tabla.NewRow();
                renglon["Codigo"] = codigo;
                renglon["Nombre"] = fila[1]!;
                renglon["Descripcion"] = (object?)fila[2] ?? DBNull.Value;
                renglon["PrecioUnitario"] = precio;
                renglon["CategoriaId"] = (object?)categoriaId ?? DBNull.Value;
                renglon["TasaISV"] = (object?)tasaIsv ?? DBNull.Value;
                renglon["StockMinimo"] = (object?)stockMinimo ?? DBNull.Value;
                tabla.Rows.Add(renglon);
            }

            if (tabla.Rows.Count == 0)
            {
                return new ResultadoImportacionDto
                {
                    Exito = erroresPrevios.Count == 0,
                    Mensaje = erroresPrevios.Count == 0 ? "El archivo no tiene filas para importar" : "Ninguna fila pudo procesarse",
                    FilasFallidas = erroresPrevios.Count,
                    Detalle = erroresPrevios
                };
            }

            using var conn = ConnectionFactory.CreateConnection();
            var parametroTabla = tabla.AsTableValuedParameter("Inventario.ProductoTableType");

            using var multi = await conn.QueryMultipleAsync(
                "Inventario.sp_ImportarProductosMasivo",
                new { Productos = parametroTabla, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);

            var resumen = await multi.ReadFirstAsync<ResultadoImportacionDto>();
            var detalle = (await multi.ReadAsync<DetalleImportacionDto>()).ToList();

            resumen.Detalle = erroresPrevios.Concat(detalle).ToList();
            resumen.FilasFallidas += erroresPrevios.Count;
            return resumen;
        }

        // Exporta un reporte completo (no es la plantilla de reimportación:
        // incluye columnas de solo lectura como StockActual/Activo).
        public static async Task<int> ExportarAExcelAsync(
            string rutaArchivo, bool soloActivos, int? categoriaId, string? busqueda)
        {
            var encabezados = new[]
            {
                "Codigo", "Nombre", "Descripcion", "PrecioUnitario", "Categoria",
                "TasaISV", "StockActual", "StockMinimo", "Activo"
            };

            var filas = new List<object?[]>();
            var pagina = 1;
            while (true)
            {
                var (productos, _) = await ListarAsync(soloActivos, categoriaId, busqueda, pagina, 500);
                foreach (var p in productos)
                {
                    filas.Add(new object?[]
                    {
                        p.Codigo, p.Nombre, p.Descripcion, p.PrecioUnitario, p.NombreCategoria,
                        p.TasaISV, p.StockActual, p.StockMinimo, p.Activo
                    });
                }

                // Se corta por página vacía, no por comparar contra "total": ese
                // valor se recalcula en cada llamada y puede correrse si hay
                // escrituras concurrentes durante una exportación larga.
                if (productos.Count < 500) break;
                pagina++;
            }

            ExcelExporter.Exportar(rutaArchivo, encabezados, filas);
            return filas.Count;
        }
    }
}
