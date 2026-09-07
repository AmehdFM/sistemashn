using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Data;
using Sistemas.Core.Security.Models;

namespace Sistemas.Core.Security
{
    public static class AuthService
    {
        // Consulta trivial de solo lectura; no amerita un stored procedure
        // dedicado (a diferencia de las operaciones que mutan datos o que
        // aplican una regla de negocio).
        public static async Task<bool> ExistenUsuariosAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            var total = await conn.ExecuteScalarAsync<int>("SELECT COUNT(1) FROM Security.Usuarios");
            return total > 0;
        }

        public static async Task<IReadOnlyList<RolDto>> ListarRolesAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            var roles = await conn.QueryAsync<RolDto>("SELECT Id, Nombre FROM Security.Roles ORDER BY Nombre");
            return roles.ToList();
        }

        public static async Task<(bool Exito, string Mensaje, SessionContext? Sesion)> AutenticarAsync(string nombreUsuario, string password)
        {
            using var conn = ConnectionFactory.CreateConnection();

            var cred = await conn.QueryFirstOrDefaultAsync<CredencialesDto>(
                "Security.sp_ObtenerCredencialesLogin",
                new { NombreUsuario = nombreUsuario },
                commandType: CommandType.StoredProcedure);

            bool credencialesValidas = cred is { Exito: true } &&
                BCrypt.Net.BCrypt.Verify(password, cred.PasswordHash);

            await conn.ExecuteAsync(
                "Security.sp_RegistrarResultadoLogin",
                new
                {
                    UsuarioId = credencialesValidas ? cred!.UsuarioId : null,
                    NombreUsuarioIntento = nombreUsuario,
                    Exito = credencialesValidas
                },
                commandType: CommandType.StoredProcedure);

            if (!credencialesValidas)
                return (false, Textos.Auth.UsuarioOPasswordIncorrectos, null);

            var sesion = new SessionContext(cred!.UsuarioId!.Value, nombreUsuario, cred.NombreCompleto!, cred.RolId!.Value, cred.NombreRol!);
            return (true, Textos.Auth.InicioSesionExitoso, sesion);
        }

        public static async Task<(bool Exito, string Mensaje, int? UsuarioId)> CrearUsuarioAsync(
            string nombreUsuario, string nombreCompleto, string password, int rolId, int? usuarioCreadorId)
        {
            var hash = BCrypt.Net.BCrypt.HashPassword(password);

            using var conn = ConnectionFactory.CreateConnection();
            var resultado = await conn.QueryFirstAsync<CrearUsuarioResultDto>(
                "Security.sp_CrearUsuario",
                new
                {
                    NombreUsuario = nombreUsuario,
                    PasswordHash = hash,
                    NombreCompleto = nombreCompleto,
                    RolId = rolId,
                    UsuarioCreadorId = usuarioCreadorId
                },
                commandType: CommandType.StoredProcedure);

            return (resultado.Exito, resultado.Mensaje, resultado.UsuarioId);
        }
    }
}
