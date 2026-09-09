using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class CompraService
    {
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
            tabla.Columns.Add("Cantidad", typeof(decimal));
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
    }
}
