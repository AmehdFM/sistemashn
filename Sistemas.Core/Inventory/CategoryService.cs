using System.Collections.Generic;
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
        // Par nombre/Id interno de la resolución en lote — vive y muere
        // dentro de ObtenerPorNombresAsync, nunca toca un control, así que
        // no hace falta que sea clase (ver LINEAMIENTOS_RENDIMIENTO.md).
        private readonly record struct CategoriaNombreId(string Nombre, int Id);

        // Resuelve en una sola query los nombres de categoría DISTINTOS que
        // ya existen (activas). Usado por la importación de Excel para
        // evitar un round-trip por fila (antes llamaba
        // ObtenerOCrearPorNombreAsync dentro del foreach). Los nombres que
        // no vengan en el diccionario resultante no existen todavía — quien
        // llama decide si los crea.
        public static async Task<Dictionary<string, int>> ObtenerPorNombresAsync(IEnumerable<string> nombres)
        {
            var distintos = nombres.Distinct(System.StringComparer.OrdinalIgnoreCase).ToList();
            var resultado = new Dictionary<string, int>(System.StringComparer.OrdinalIgnoreCase);
            if (distintos.Count == 0) return resultado;

            using var conn = ConnectionFactory.CreateConnection();
            var filas = await conn.QueryAsync(
                "SELECT Nombre, Id FROM Inventario.Categorias WHERE Nombre IN @Nombres AND Activo = 1",
                new { Nombres = distintos });

            foreach (var fila in filas)
            {
                var par = new CategoriaNombreId((string)fila.Nombre, (int)fila.Id);
                resultado[par.Nombre] = par.Id;
            }

            return resultado;
        }

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
