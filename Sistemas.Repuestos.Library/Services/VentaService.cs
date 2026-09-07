using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
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
        // y la tasa de ISV se congelan del lado del servidor.
        public static async Task<(bool Exito, string Mensaje, string? NumeroFactura, decimal? Total)> RegistrarAsync(
            IReadOnlyList<LineaCarritoDto> detalle, bool esCredito, int? diasCredito, int usuarioId, int? clienteId = null)
        {
            var tabla = new DataTable();
            tabla.Columns.Add("ProductoId", typeof(int));
            tabla.Columns.Add("Cantidad", typeof(int));
            foreach (var linea in detalle)
                tabla.Rows.Add(linea.ProductoId, linea.Cantidad);

            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, string? NumeroFactura, decimal? Total)>(
                "Repuestos.sp_RegistrarVenta",
                new
                {
                    UsuarioId = usuarioId,
                    EsCredito = esCredito,
                    DiasCredito = diasCredito,
                    ClienteId = clienteId,
                    Detalle = tabla.AsTableValuedParameter("Repuestos.VentaDetalleTableType")
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
    }
}
