using System;
using System.Collections.Generic;
using System.Data;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Export;
using Sistemas.Core.Inventory;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class CompraService
    {
        // Columnas exactas de la plantilla de importación de compras — una
        // fila de Excel es una línea de producto; las filas con el mismo
        // Proveedor+NumeroFacturaProveedor se agrupan en una sola compra
        // (mismo patrón que ProductService.EncabezadosImportacion en
        // Sistemas.Core, aplicado a compras).
        public static readonly string[] EncabezadosImportacionCompras =
            { "Proveedor", "NumeroFacturaProveedor", "EsCredito", "DiasCredito", "Codigo", "Cantidad", "CostoUnitario" };

        // Clave de agrupación Proveedor+NúmeroFactura — vive y muere dentro
        // de ImportarDesdeExcelAsync, nunca se bindea a ningún control, así
        // que va como readonly record struct (ver LINEAMIENTOS_RENDIMIENTO.md).
        private readonly record struct ClaveCompra(string Proveedor, string? NumeroFactura);

        // Una fila de Excel ya validada, previa al agrupamiento. También
        // interna al método — mismo motivo, readonly record struct.
        private readonly record struct FilaCompraValidada(
            string Proveedor, string? NumeroFactura, bool EsCredito, int? DiasCredito,
            string Codigo, int Cantidad, decimal CostoUnitario);

        public static async Task<(List<CompraDto> Compras, int TotalFilas)> ListarAsync(
            int? proveedorId, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarCompras",
                new { ProveedorId = proveedorId, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var compras = (await multi.ReadAsync<CompraDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (compras, total);
        }

        public static async Task<(bool Exito, string Mensaje, int? CompraId)> RegistrarAsync(
            int proveedorId, string? numeroFacturaProveedor, bool esCredito, int? diasCredito,
            IReadOnlyList<LineaCompraDto> detalle, int usuarioId)
        {
            var tabla = new DataTable();
            tabla.Columns.Add("ProductoId", typeof(int));
            tabla.Columns.Add("Cantidad", typeof(int));
            tabla.Columns.Add("CostoUnitario", typeof(decimal));
            foreach (var linea in detalle)
                tabla.Rows.Add(linea.ProductoId, linea.Cantidad, linea.CostoUnitario);

            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? CompraId)>(
                "Repuestos.sp_RegistrarCompra",
                new
                {
                    ProveedorId = proveedorId,
                    NumeroFacturaProveedor = numeroFacturaProveedor,
                    UsuarioId = usuarioId,
                    EsCredito = esCredito,
                    DiasCredito = diasCredito,
                    Detalle = tabla.AsTableValuedParameter("Repuestos.CompraDetalleTableType")
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<ResultadoImportacionComprasDto> ImportarDesdeExcelAsync(string rutaArchivo, int usuarioId)
        {
            // Síncrono (ClosedXML no tiene API async): se envuelve en
            // Task.Run para no bloquear el hilo de UI mientras parsea
            // (mismo fix que ProductService.ImportarDesdeExcelAsync).
            var (coincide, error, filas) = await Task.Run(() => ExcelExporter.LeerHoja(rutaArchivo, EncabezadosImportacionCompras));
            if (!coincide)
            {
                return new ResultadoImportacionComprasDto { Exito = false, Mensaje = error ?? "El archivo no tiene la estructura esperada" };
            }

            var erroresPrevios = new List<DetalleImportacionCompraDto>();
            var filasValidas = new List<FilaCompraValidada>();

            for (var i = 0; i < filas.Count; i++)
            {
                var fila = filas[i];
                var identificadorFila = "Fila " + (i + 2); // la fila 1 es el encabezado

                var proveedor = fila[0];
                if (string.IsNullOrWhiteSpace(proveedor))
                {
                    erroresPrevios.Add(new DetalleImportacionCompraDto { Identificador = identificadorFila, Exito = false, Mensaje = "Proveedor vacío", CantidadLineas = 1 });
                    continue;
                }

                var codigo = fila[4];
                if (string.IsNullOrWhiteSpace(codigo))
                {
                    erroresPrevios.Add(new DetalleImportacionCompraDto { Identificador = identificadorFila, Exito = false, Mensaje = "Código vacío", CantidadLineas = 1 });
                    continue;
                }

                if (!int.TryParse(fila[5], NumberStyles.Integer, CultureInfo.InvariantCulture, out var cantidad) || cantidad <= 0)
                {
                    erroresPrevios.Add(new DetalleImportacionCompraDto { Identificador = identificadorFila, Exito = false, Mensaje = "Cantidad inválida (debe ser un entero positivo)", CantidadLineas = 1 });
                    continue;
                }

                if (!decimal.TryParse(fila[6], NumberStyles.Any, CultureInfo.InvariantCulture, out var costoUnitario) || costoUnitario < 0)
                {
                    erroresPrevios.Add(new DetalleImportacionCompraDto { Identificador = identificadorFila, Exito = false, Mensaje = "Costo unitario inválido", CantidadLineas = 1 });
                    continue;
                }

                var esCredito = false;
                if (!string.IsNullOrWhiteSpace(fila[2]))
                {
                    if (!bool.TryParse(fila[2], out esCredito))
                    {
                        erroresPrevios.Add(new DetalleImportacionCompraDto { Identificador = identificadorFila, Exito = false, Mensaje = "EsCredito inválido (use true/false)", CantidadLineas = 1 });
                        continue;
                    }
                }

                int? diasCredito = null;
                if (!string.IsNullOrWhiteSpace(fila[3]))
                {
                    if (!int.TryParse(fila[3], NumberStyles.Integer, CultureInfo.InvariantCulture, out var dias) || dias <= 0)
                    {
                        erroresPrevios.Add(new DetalleImportacionCompraDto { Identificador = identificadorFila, Exito = false, Mensaje = "DiasCredito inválido", CantidadLineas = 1 });
                        continue;
                    }
                    diasCredito = dias;
                }

                filasValidas.Add(new FilaCompraValidada(
                    proveedor!.Trim(),
                    string.IsNullOrWhiteSpace(fila[1]) ? null : fila[1]!.Trim(),
                    esCredito, diasCredito, codigo!.Trim(), cantidad, costoUnitario));
            }

            if (filasValidas.Count == 0)
            {
                return new ResultadoImportacionComprasDto
                {
                    Exito = erroresPrevios.Count == 0,
                    Mensaje = erroresPrevios.Count == 0 ? "El archivo no tiene filas para importar" : "Ninguna fila pudo procesarse",
                    ComprasFallidas = erroresPrevios.Count,
                    Detalle = erroresPrevios
                };
            }

            // Resolución en lote (no N+1): todos los proveedores distintos
            // contra una sola llamada a ListarProveedoresAsync, todos los
            // códigos de producto distintos contra sp_BuscarProductosPorCodigos
            // en una sola llamada — antes de agrupar/registrar ninguna compra.
            var (proveedores, _) = await TerceroService.ListarProveedoresAsync(true, null, 1, 500);
            var proveedoresPorNombre = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (var p in proveedores)
                proveedoresPorNombre.TryAdd(p.Nombre, p.Id);

            var codigosDistintos = filasValidas.Select(f => f.Codigo).Distinct(StringComparer.OrdinalIgnoreCase);
            var productosPorCodigo = await ProductService.BuscarPorCodigosAsync(codigosDistintos);

            // Cada grupo Proveedor+NumeroFacturaProveedor arma una sola
            // compra con todas sus líneas — igual que arma una compra
            // FormRegistrarCompra.cs, solo que desde muchas filas de Excel.
            var grupos = filasValidas.GroupBy(f => new ClaveCompra(f.Proveedor, f.NumeroFactura));

            var detalle = new List<DetalleImportacionCompraDto>(erroresPrevios);
            var exitosas = 0;
            var fallidas = erroresPrevios.Count;

            foreach (var grupo in grupos)
            {
                var clave = grupo.Key;
                var lineasGrupo = grupo.ToList();
                var identificador = clave.Proveedor + " — " + (clave.NumeroFactura ?? "(sin número)");

                if (!proveedoresPorNombre.TryGetValue(clave.Proveedor, out var proveedorId))
                {
                    detalle.Add(new DetalleImportacionCompraDto { Identificador = identificador, Exito = false, Mensaje = "Proveedor no encontrado: " + clave.Proveedor, CantidadLineas = lineasGrupo.Count });
                    fallidas++;
                    continue;
                }

                var codigosNoEncontrados = lineasGrupo
                    .Select(l => l.Codigo)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Where(c => !productosPorCodigo.ContainsKey(c))
                    .ToList();

                if (codigosNoEncontrados.Count > 0)
                {
                    detalle.Add(new DetalleImportacionCompraDto { Identificador = identificador, Exito = false, Mensaje = "Código(s) no encontrado(s): " + string.Join(", ", codigosNoEncontrados), CantidadLineas = lineasGrupo.Count });
                    fallidas++;
                    continue;
                }

                var lineas = lineasGrupo.Select(l =>
                {
                    var producto = productosPorCodigo[l.Codigo];
                    return new LineaCompraDto
                    {
                        ProductoId = producto.Id,
                        Codigo = producto.Codigo,
                        Nombre = producto.Nombre,
                        Cantidad = l.Cantidad,
                        CostoUnitario = l.CostoUnitario
                    };
                }).ToList();

                // EsCredito/DiasCredito son propiedades de la compra, no de
                // la línea: se toman de la primera fila del grupo (todas las
                // filas de una misma factura deberían traer el mismo valor).
                var primera = lineasGrupo[0];

                var (exito, mensaje, _) = await RegistrarAsync(
                    proveedorId, clave.NumeroFactura, primera.EsCredito, primera.DiasCredito, lineas, usuarioId);

                detalle.Add(new DetalleImportacionCompraDto { Identificador = identificador, Exito = exito, Mensaje = mensaje, CantidadLineas = lineasGrupo.Count });
                if (exito) exitosas++; else fallidas++;
            }

            return new ResultadoImportacionComprasDto
            {
                Exito = fallidas == 0,
                Mensaje = $"{exitosas} compra(s) registrada(s), {fallidas} fallida(s)",
                ComprasExitosas = exitosas,
                ComprasFallidas = fallidas,
                Detalle = detalle
            };
        }

        // Exporta el historial de compras — mismo patrón paginado que
        // ProductService.ExportarAExcelAsync.
        public static async Task<int> ExportarAExcelAsync(string rutaArchivo, int? proveedorId)
        {
            var encabezados = new[] { "Fecha", "Proveedor", "NumeroFacturaProveedor", "Total", "EsCredito" };

            var filas = new List<object?[]>();
            var pagina = 1;
            while (true)
            {
                var (compras, _) = await ListarAsync(proveedorId, pagina, 500);
                foreach (var c in compras)
                {
                    filas.Add(new object?[] { c.Fecha, c.NombreProveedor, c.NumeroFacturaProveedor, c.Total, c.EsCredito });
                }

                // Se corta por página vacía, no por comparar contra "total"
                // (mismo criterio que ProductService.ExportarAExcelAsync).
                if (compras.Count < 500) break;
                pagina++;
            }

            ExcelExporter.Exportar(rutaArchivo, encabezados, filas);
            return filas.Count;
        }

        // Solo genera la plantilla en blanco — no va a la base de datos.
        public static Task GenerarPlantillaAsync(string rutaArchivo)
        {
            ExcelExporter.GenerarPlantilla(rutaArchivo, EncabezadosImportacionCompras);
            return Task.CompletedTask;
        }
    }
}
