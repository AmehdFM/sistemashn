using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    // Capa delgada sobre las sesiones de caja: cada método es un passthrough
    // 1:1 a un SP de Repuestos — ninguna regla de negocio ni cálculo se
    // repite aquí (quién puede abrir/cerrar, el monto esperado, la
    // diferencia, todo lo decide el SP).
    public static class CajaService
    {
        public static async Task<(bool Exito, string Mensaje, int? SesionCajaId)> AbrirAsync(decimal montoApertura, int usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? SesionCajaId)>(
                "Repuestos.sp_AbrirCaja",
                new { UsuarioId = usuarioId, MontoApertura = montoApertura },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje, decimal? MontoCierreCalculado, decimal? Diferencia)> CerrarAsync(
            int sesionCajaId, decimal montoCierreDeclarado, int usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, decimal? MontoCierreCalculado, decimal? Diferencia)>(
                "Repuestos.sp_CerrarCaja",
                new { SesionCajaId = sesionCajaId, UsuarioId = usuarioId, MontoCierreDeclarado = montoCierreDeclarado },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<SesionCajaDto?> ObtenerAbiertaAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstOrDefaultAsync<SesionCajaDto>(
                "Repuestos.sp_ObtenerSesionCajaAbierta",
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<decimal> ObtenerMontoEsperadoAsync(int sesionCajaId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<decimal>(
                "Repuestos.sp_ObtenerMontoEsperadoCaja",
                new { SesionCajaId = sesionCajaId },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(List<SesionCajaDto> Sesiones, int TotalFilas)> ListarAsync(int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarSesionesCaja",
                new { Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var sesiones = (await multi.ReadAsync<SesionCajaDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (sesiones, total);
        }
    }
}
