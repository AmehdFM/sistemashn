using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class CuentaPorCobrarService
    {
        public static async Task<(List<CuentaPorCobrarDto> Cuentas, int TotalFilas)> ListarAsync(
            bool soloConSaldo, int pagina, int tamanoPagina, int? clienteId = null)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarCuentasPorCobrar",
                new { SoloConSaldo = soloConSaldo, Pagina = pagina, TamanoPagina = tamanoPagina, ClienteId = clienteId },
                commandType: CommandType.StoredProcedure);

            var cuentas = (await multi.ReadAsync<CuentaPorCobrarDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (cuentas, total);
        }

        public static async Task<(bool Exito, string Mensaje)> RegistrarPagoAsync(
            int cuentaPorCobrarId, decimal monto, string? metodoPago, int usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Repuestos.sp_RegistrarPagoCuentaPorCobrar",
                new { CuentaPorCobrarId = cuentaPorCobrarId, Monto = monto, MetodoPago = metodoPago, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
        }
    }
}
