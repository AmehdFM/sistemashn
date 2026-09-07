using System;
using System.Data;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Facturacion.Models;

namespace Sistemas.Core.Facturacion
{
    public static class FacturacionService
    {
        public static async Task<ConfiguracionCaiDto> ObtenerConfiguracionAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<ConfiguracionCaiDto>(
                "Facturacion.sp_ObtenerConfiguracionCAI", commandType: CommandType.StoredProcedure);
        }

        // Un CAI se reemplaza, no se edita: el SAR emite rangos fijos nuevos
        // cuando el anterior se agota o vence.
        public static async Task<(bool Exito, string Mensaje)> GuardarConfiguracionAsync(
            string rangoAutorizado, string rangoInicial, string rangoFinal,
            DateTime fechaAutorizacion, DateTime fechaVencimiento, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Facturacion.sp_GuardarConfiguracionCAI",
                new
                {
                    RangoAutorizado = rangoAutorizado,
                    RangoInicial = rangoInicial,
                    RangoFinal = rangoFinal,
                    FechaAutorizacion = fechaAutorizacion,
                    FechaVencimiento = fechaVencimiento,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }
    }
}
