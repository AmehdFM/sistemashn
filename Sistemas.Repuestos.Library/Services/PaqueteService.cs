using System.Collections.Generic;
using System.Data;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Repuestos.Library.Models;

namespace Sistemas.Repuestos.Library.Services
{
    public static class PaqueteService
    {
        // Si el SP rechaza porque el paquete ya tiene ventas registradas, el
        // mensaje se devuelve tal cual (no hay forma de comprobarlo antes sin
        // un SP dedicado).
        public static async Task<(bool Exito, string Mensaje)> ArmarAsync(
            int productoIdPaquete, IReadOnlyList<ComponentePaqueteDto> componentes, int usuarioId)
        {
            var tabla = new DataTable();
            tabla.Columns.Add("ComponenteProductoId", typeof(int));
            tabla.Columns.Add("Cantidad", typeof(decimal));
            foreach (var componente in componentes)
                tabla.Rows.Add(componente.ComponenteProductoId, componente.Cantidad);

            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Repuestos.sp_ArmarPaquete",
                new
                {
                    ProductoIdPaquete = productoIdPaquete,
                    UsuarioId = usuarioId,
                    Componentes = tabla.AsTableValuedParameter("Repuestos.PaqueteDetalleTableType")
                },
                commandType: CommandType.StoredProcedure);
        }
    }
}
