using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class CuentaPorPagarService
    {
        public static async Task<(List<CuentaPorPagarDto> Cuentas, int TotalFilas)> ListarAsync(
            bool soloConSaldo, int pagina, int tamanoPagina, int? proveedorId = null)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarCuentasPorPagar",
                new { SoloConSaldo = soloConSaldo, Pagina = pagina, TamanoPagina = tamanoPagina, ProveedorId = proveedorId },
                commandType: CommandType.StoredProcedure);

            var cuentas = (await multi.ReadAsync<CuentaPorPagarDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (cuentas, total);
        }

        public static async Task<(bool Exito, string Mensaje)> RegistrarPagoAsync(
            int cuentaPorPagarId, decimal monto, string? metodoPago, int usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Repuestos.sp_RegistrarPagoCuentaPorPagar",
                new { CuentaPorPagarId = cuentaPorPagarId, Monto = monto, MetodoPago = metodoPago, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
        }
    }
}
