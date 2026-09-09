using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Inventory.Models;

namespace Sistemas.Core.Inventory
{
    public static class UnidadMedidaService
    {
        public static async Task<List<UnidadMedidaDto>> ObtenerActivasAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            var resultado = await conn.QueryAsync<UnidadMedidaDto>(
                "Inventario.sp_ListarUnidadesMedida",
                new { SoloActivas = true },
                commandType: CommandType.StoredProcedure);
            return resultado.ToList();
        }

        public static async Task<List<UnidadMedidaDto>> ListarAsync(bool soloActivas)
        {
            using var conn = ConnectionFactory.CreateConnection();
            var resultado = await conn.QueryAsync<UnidadMedidaDto>(
                "Inventario.sp_ListarUnidadesMedida",
                new { SoloActivas = soloActivas },
                commandType: CommandType.StoredProcedure);
            return resultado.ToList();
        }

        public static async Task<(bool Exito, string Mensaje, int? UnidadMedidaId)> CrearAsync(
            string codigo, string nombre, string simbolo, bool permiteFraccion, string? sistema, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? UnidadMedidaId)>(
                "Inventario.sp_CrearUnidadMedida",
                new
                {
                    Codigo = codigo,
                    Nombre = nombre,
                    Simbolo = simbolo,
                    PermiteFraccion = permiteFraccion,
                    Sistema = sistema,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje)> ActualizarAsync(
            int unidadMedidaId, string nombre, string simbolo, bool permiteFraccion, string? sistema, bool activo, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Inventario.sp_ActualizarUnidadMedida",
                new
                {
                    UnidadMedidaId = unidadMedidaId,
                    Nombre = nombre,
                    Simbolo = simbolo,
                    PermiteFraccion = permiteFraccion,
                    Sistema = sistema,
                    Activo = activo,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }
    }
}
