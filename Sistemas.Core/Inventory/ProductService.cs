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
            { "Codigo", "Nombre", "Descripcion", "PrecioUnitario", "Categoria", "TasaISV", "StockMinimo", "UnidadMedida" };

        // Filas de ejemplo para la plantilla descargable — no basta con los
        // encabezados solos, hace falta mostrar el TIPO de dato esperado en
        // cada columna (formato de número, qué va en Categoria/UnidadMedida).
        public static readonly object?[][] FilasEjemploImportacion =
        {
            new object?[] { "TOR-001", "Tornillo hexagonal 1/4\"", "Tornillo hexagonal galvanizado de 1/4 pulgada", 5.50m, "Ferretería", 15m, 100m, "UNI" },
            new object?[] { "PIN-002", "Pintura de aceite blanca", "Pintura de aceite color blanco, cubeta", 950.00m, "Pinturas", 15m, 10.5m, "GAL" },
            new object?[] { "CEM-003", "Cemento gris", "Cemento gris para construcción", 180.00m, "Materiales de construcción", 15m, 25m, "QQ" }
        };

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
            int? categoriaId, decimal tasaIsv, decimal stockMinimo, int unidadMedidaId, int? usuarioId,
            string? codigoBarra = null)
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
                    UnidadMedidaId = unidadMedidaId,
                    UsuarioId = usuarioId,
                    CodigoBarra = codigoBarra
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje)> ActualizarAsync(
            int productoId, string nombre, string? descripcion, decimal precioUnitario,
            int? categoriaId, decimal tasaIsv, decimal stockMinimo, int unidadMedidaId, bool activo, int? usuarioId,
            string? codigoBarra = null)
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
                    UnidadMedidaId = unidadMedidaId,
                    Activo = activo,
                    UsuarioId = usuarioId,
                    CodigoBarra = codigoBarra
                },
                commandType: CommandType.StoredProcedure);
        }

        // Match exacto (Codigo o CodigoBarra) para lectores de código de
        // barras en el POS — a diferencia de ListarAsync, nunca devuelve más
        // de una fila. La comparación exacta-vs-parcial vive en el SP, no
        // aquí: este método solo decide llamarlo primero.
        public static async Task<ProductoDto?> BuscarPorCodigoExactoAsync(string codigo)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstOrDefaultAsync<ProductoDto>(
                "Inventario.sp_BuscarProductoPorCodigo",
                new { Codigo = codigo },
                commandType: CommandType.StoredProcedure);
        }

        // Resuelve un lote de códigos de producto en una sola llamada —
        // mismo patrón TVP que Repuestos.CompraDetalleTableType/
        // VentaDetalleTableType. Usado por la importación de compras desde
        // Excel (Sistemas.Repuestos.Library) para no ir a la base una vez
        // por código. Los códigos que no vengan en el diccionario resultante
        // no existen.
        public static async Task<Dictionary<string, ProductoResumenDto>> BuscarPorCodigosAsync(IEnumerable<string> codigos)
        {
            var distintos = codigos.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            var resultado = new Dictionary<string, ProductoResumenDto>(StringComparer.OrdinalIgnoreCase);
            if (distintos.Count == 0) return resultado;

            var tabla = new DataTable();
            tabla.Columns.Add("Codigo", typeof(string));
            foreach (var codigo in distintos)
                tabla.Rows.Add(codigo);

            using var conn = ConnectionFactory.CreateConnection();
            var filas = await conn.QueryAsync(
                "Inventario.sp_BuscarProductosPorCodigos",
                new { Codigos = tabla.AsTableValuedParameter("Inventario.CodigoTableType") },
                commandType: CommandType.StoredProcedure);

            foreach (var fila in filas)
            {
                var producto = new ProductoResumenDto((int)fila.Id, (string)fila.Codigo, (string)fila.Nombre, (decimal)fila.PrecioUnitario);
                resultado[producto.Codigo] = producto;
            }

            return resultado;
        }

        public static async Task<ResultadoImportacionDto> ImportarDesdeExcelAsync(string rutaArchivo, int usuarioId)
        {
            // Síncrono (ClosedXML no tiene API async): se envuelve en
            // Task.Run para no bloquear el hilo de UI mientras parsea.
            var (coincide, error, filas) = await Task.Run(() => ExcelExporter.LeerHoja(rutaArchivo, EncabezadosImportacion));
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
            tabla.Columns.Add("StockMinimo", typeof(decimal));
            tabla.Columns.Add("UnidadMedidaCodigo", typeof(string));

            var erroresPrevios = new List<DetalleImportacionDto>();

            // Resolución en lote de categorías (fix N+1): antes se llamaba
            // CategoryService.ObtenerOCrearPorNombreAsync dentro del foreach
            // de abajo, un round-trip a SQL Server por cada fila con
            // categoría. Ahora se sacan los nombres DISTINTOS no vacíos del
            // archivo, se resuelven las existentes en una sola query y se
            // crean solo las que faltan (normalmente pocas) — el foreach de
            // filas solo hace lookup en el diccionario ya armado.
            var nombresCategoria = filas
                .Select(f => f[4])
                .Where(n => !string.IsNullOrWhiteSpace(n))
                .Select(n => n!.Trim())
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();

            var categoriasPorNombre = await CategoryService.ObtenerPorNombresAsync(nombresCategoria);
            var categoriasFallidas = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            foreach (var nombreCategoria in nombresCategoria)
            {
                if (categoriasPorNombre.ContainsKey(nombreCategoria)) continue;

                var (exitoCat, mensajeCat, idCat) = await CategoryService.CrearAsync(nombreCategoria, null, usuarioId);
                if (exitoCat && idCat.HasValue)
                    categoriasPorNombre[nombreCategoria] = idCat.Value;
                else
                    categoriasFallidas[nombreCategoria] = mensajeCat;
            }

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
                    var nombreCategoria = fila[4]!.Trim();
                    if (categoriasPorNombre.TryGetValue(nombreCategoria, out var idCat))
                    {
                        categoriaId = idCat;
                    }
                    else
                    {
                        var mensajeCat = categoriasFallidas.TryGetValue(nombreCategoria, out var m) ? m : "categoría desconocida";
                        erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "No se pudo resolver la categoría: " + mensajeCat });
                        continue;
                    }
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

                decimal? stockMinimo = null;
                if (!string.IsNullOrWhiteSpace(fila[6]))
                {
                    if (!decimal.TryParse(fila[6], NumberStyles.Any, CultureInfo.InvariantCulture, out var stock) || stock < 0)
                    {
                        erroresPrevios.Add(new DetalleImportacionDto { Codigo = codigo, Exito = false, Mensaje = "Stock mínimo inválido" });
                        continue;
                    }
                    stockMinimo = stock;
                }

                var unidadMedidaCodigo = string.IsNullOrWhiteSpace(fila[7]) ? null : fila[7]!.Trim().ToUpperInvariant();

                var renglon = tabla.NewRow();
                renglon["Codigo"] = codigo;
                renglon["Nombre"] = fila[1]!;
                renglon["Descripcion"] = (object?)fila[2] ?? DBNull.Value;
                renglon["PrecioUnitario"] = precio;
                renglon["CategoriaId"] = (object?)categoriaId ?? DBNull.Value;
                renglon["TasaISV"] = (object?)tasaIsv ?? DBNull.Value;
                renglon["StockMinimo"] = (object?)stockMinimo ?? DBNull.Value;
                renglon["UnidadMedidaCodigo"] = (object?)unidadMedidaCodigo ?? DBNull.Value;
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
