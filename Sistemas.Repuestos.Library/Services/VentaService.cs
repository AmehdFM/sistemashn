using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Export;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class VentaService
    {
        public static async Task<(List<VentaDto> Ventas, int TotalFilas)> ListarAsync(
            string? numeroFactura, bool soloVigentes, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarVentas",
                new { NumeroFactura = numeroFactura, SoloVigentes = soloVigentes, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var ventas = (await multi.ReadAsync<VentaDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (ventas, total);
        }

        // El carrito solo envía ProductoId+Cantidad — nunca precio: el precio
        // y la tasa de ISV se congelan del lado del servidor. El Vuelto
        // tampoco se envía: lo calcula sp_RegistrarVenta a partir del total
        // real que él mismo determina, y es ese valor (no el que mostró la
        // calculadora de cambio en pantalla) el que vuelve en la respuesta.
        public static async Task<(bool Exito, string Mensaje, string? NumeroFactura, decimal? Total, decimal? EfectivoRecibido, decimal? Vuelto)> RegistrarAsync(
            IReadOnlyList<LineaCarritoDto> detalle, bool esCredito, int? diasCredito, int usuarioId, int? clienteId,
            string metodoPago, decimal? efectivoRecibido)
        {
            var tabla = new DataTable();
            tabla.Columns.Add("ProductoId", typeof(int));
            tabla.Columns.Add("Cantidad", typeof(decimal));
            foreach (var linea in detalle)
                tabla.Rows.Add(linea.ProductoId, linea.Cantidad);

            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, string? NumeroFactura, decimal? Total, decimal? EfectivoRecibido, decimal? Vuelto)>(
                "Repuestos.sp_RegistrarVenta",
                new
                {
                    UsuarioId = usuarioId,
                    EsCredito = esCredito,
                    DiasCredito = diasCredito,
                    ClienteId = clienteId,
                    Detalle = tabla.AsTableValuedParameter("Repuestos.VentaDetalleTableType"),
                    MetodoPago = metodoPago,
                    EfectivoRecibido = efectivoRecibido
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje)> AnularAsync(int ventaId, string motivo, int usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Repuestos.sp_AnularVenta",
                new { VentaId = ventaId, UsuarioId = usuarioId, Motivo = motivo },
                commandType: CommandType.StoredProcedure);
        }

        // Solo exporta — no hay ImportarDesdeExcelAsync para ventas: una
        // venta involucra reglas que no tiene sentido saltarse en lote
        // (precio congelado en servidor, correlativo CAI, descuento de
        // stock en tiempo real, sesión de caja obligatoria), así que las
        // ventas siempre se registran una por una en el POS.
        public static async Task<int> ExportarAExcelAsync(string? numeroFactura, bool soloVigentes, string rutaArchivo)
        {
            var encabezados = new[] { "NumeroFactura", "Fecha", "Total", "EsCredito", "MetodoPago", "Anulada" };

            var filas = new List<object?[]>();
            var pagina = 1;
            while (true)
            {
                var (ventas, _) = await ListarAsync(numeroFactura, soloVigentes, pagina, 500);
                foreach (var v in ventas)
                {
                    filas.Add(new object?[]
                    {
                        v.NumeroFactura, v.Fecha, v.Total, v.EsCredito, v.MetodoPago, v.Anulada
                    });
                }

                // Se corta por página vacía, no por comparar contra "total"
                // (mismo criterio que ProductService.ExportarAExcelAsync):
                // ese valor puede correrse si hay escrituras concurrentes
                // durante una exportación larga.
                if (ventas.Count < 500) break;
                pagina++;
            }

            ExcelExporter.Exportar(rutaArchivo, encabezados, filas);
            return filas.Count;
        }
    }
}
