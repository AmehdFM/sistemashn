using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class TerceroService
    {
        public static async Task<(List<TerceroDto> Terceros, int TotalFilas)> ListarProveedoresAsync(
            bool soloActivos, string? busqueda, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarProveedores",
                new { SoloActivos = soloActivos, Busqueda = busqueda, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var terceros = (await multi.ReadAsync<TerceroDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (terceros, total);
        }

        public static async Task<(List<TerceroDto> Terceros, int TotalFilas)> ListarClientesAsync(
            bool soloActivos, string? busqueda, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarClientes",
                new { SoloActivos = soloActivos, Busqueda = busqueda, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var terceros = (await multi.ReadAsync<TerceroDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (terceros, total);
        }

        public static async Task<(bool Exito, string Mensaje, int? TerceroId)> GuardarAsync(
            int? terceroId, string nombre, string? empresa, string? correo, string? telefono, string? rtn,
            bool esProveedor, bool esCliente, bool activo, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? TerceroId)>(
                "Repuestos.sp_GuardarTercero",
                new
                {
                    TerceroId = terceroId,
                    Nombre = nombre,
                    Empresa = empresa,
                    Correo = correo,
                    Telefono = telefono,
                    RTN = rtn,
                    EsProveedor = esProveedor,
                    EsCliente = esCliente,
                    Activo = activo,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }

        public static async Task<List<PrecioProveedorDto>> CompararPreciosAsync(int productoId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            var resultado = await conn.QueryAsync<PrecioProveedorDto>(
                "Repuestos.sp_CompararPreciosProveedor",
                new { ProductoId = productoId },
                commandType: CommandType.StoredProcedure);
            return resultado.ToList();
        }

        public static async Task<(bool Exito, string Mensaje)> GuardarPrecioAsync(
            int productoId, int proveedorId, decimal precioCompra, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Repuestos.sp_GuardarPrecioProveedor",
                new { ProductoId = productoId, ProveedorId = proveedorId, PrecioCompra = precioCompra, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
        }
    }
}
