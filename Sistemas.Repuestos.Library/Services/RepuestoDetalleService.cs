using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class RepuestoDetalleService
    {
        public static async Task<RepuestoDetalleDto> ObtenerAsync(int productoId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ObtenerProductoRepuesto",
                new { ProductoId = productoId },
                commandType: CommandType.StoredProcedure);

            var detalle = await multi.ReadFirstAsync<RepuestoDetalleDto>();
            detalle.Vehiculos = (await multi.ReadAsync<VehiculoCompatibleDto>()).ToList();
            detalle.Equivalentes = (await multi.ReadAsync<NumeroEquivalenteDto>()).ToList();
            return detalle;
        }

        public static async Task<(bool Exito, string Mensaje)> GuardarDetalleAsync(
            int productoId, string? numeroParte, string? marcaFabricante, bool esOriginal, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Repuestos.sp_GuardarDetalleProducto",
                new { ProductoId = productoId, NumeroParte = numeroParte, MarcaFabricante = marcaFabricante, EsOriginal = esOriginal, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje, int? VehiculoCompatibleId)> AgregarVehiculoAsync(
            int productoId, string marca, string modelo, int anioDesde, int anioHasta, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? VehiculoCompatibleId)>(
                "Repuestos.sp_AgregarVehiculoCompatible",
                new { ProductoId = productoId, Marca = marca, Modelo = modelo, AnioDesde = anioDesde, AnioHasta = anioHasta, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(bool Exito, string Mensaje, int? NumeroEquivalenteId)> AgregarEquivalenteAsync(
            int productoId, string numeroOEM, string? fabricante, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? NumeroEquivalenteId)>(
                "Repuestos.sp_AgregarNumeroEquivalente",
                new { ProductoId = productoId, NumeroOEM = numeroOEM, Fabricante = fabricante, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<(List<EquivalenciaResultadoDto> Resultados, int TotalFilas)> BuscarPorEquivalenciaAsync(
            string numero, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_BuscarPorEquivalencia",
                new { Numero = numero, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var resultados = (await multi.ReadAsync<EquivalenciaResultadoDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (resultados, total);
        }
    }
}
