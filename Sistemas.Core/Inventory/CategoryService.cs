using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Inventory.Models;

namespace Sistemas.Core.Inventory
{
    public static class CategoryService
    {
        // Lectura trivial de solo lectura, sin regla de negocio — no amerita
        // un stored procedure dedicado (igual que AuthService.ListarRolesAsync).
        public static async Task<System.Collections.Generic.List<CategoriaDto>> ListarAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            var categorias = await conn.QueryAsync<CategoriaDto>(
                "SELECT Id, Nombre, CategoriaPadreId FROM Inventario.Categorias WHERE Activo = 1 ORDER BY Nombre");
            return categorias.ToList();
        }

        public static async Task<(bool Exito, string Mensaje, int? CategoriaId)> CrearAsync(
            string nombre, int? categoriaPadreId, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            var resultado = await conn.QueryFirstAsync<(bool Exito, string Mensaje, int? CategoriaId)>(
                "Inventario.sp_CrearCategoria",
                new { Nombre = nombre, CategoriaPadreId = categoriaPadreId, UsuarioId = usuarioId },
                commandType: CommandType.StoredProcedure);
            return resultado;
        }

        // Usado por la importación de Excel: busca la categoría por nombre
        // exacto y, si no existe, la crea.
        public static async Task<(bool Exito, string Mensaje, int? CategoriaId)> ObtenerOCrearPorNombreAsync(
            string nombre, int? usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            var existente = await conn.QueryFirstOrDefaultAsync<int?>(
                "SELECT TOP (1) Id FROM Inventario.Categorias WHERE Nombre = @Nombre AND Activo = 1", new { Nombre = nombre });

            if (existente.HasValue)
                return (true, "Categoría existente", existente.Value);

            return await CrearAsync(nombre, null, usuarioId);
        }
    }
}
