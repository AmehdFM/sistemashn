using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class ProveedorService
    {
        public static async Task<(List<ProveedorDto> Proveedores, int TotalFilas)> ListarAsync(
            bool soloActivos, string? busqueda, int pagina, int tamanoPagina)
        {
            using var conn = ConnectionFactory.CreateConnection();
            using var multi = await conn.QueryMultipleAsync(
                "Repuestos.sp_ListarProveedores",
                new { SoloActivos = soloActivos, Busqueda = busqueda, Pagina = pagina, TamanoPagina = tamanoPagina },
                commandType: CommandType.StoredProcedure);

            var proveedores = (await multi.ReadAsync<ProveedorDto>()).ToList();
            var total = await multi.ReadFirstAsync<int>();
            return (proveedores, total);
        }

        public static async Task<(bool Exito, string Mensaje, int? ProveedorId)> GuardarAsync(
            int? proveedorId, string nombre, string? rtn, string? telefono, string? contacto, bool activo, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? ProveedorId)>(
                "Repuestos.sp_GuardarProveedor",
                new
                {
                    ProveedorId = proveedorId,
                    Nombre = nombre,
                    RTN = rtn,
                    Telefono = telefono,
                    Contacto = contacto,
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
