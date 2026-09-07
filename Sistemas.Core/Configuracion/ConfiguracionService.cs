using System.Data;
using System.Threading.Tasks;
using Dapper;
using Sistemas.Core.Configuracion.Models;
using Sistemas.Core.Data;

namespace Sistemas.Core.Configuracion
{
    public static class ConfiguracionService
    {
        public static async Task<ConfiguracionDto> ObtenerAsync()
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<ConfiguracionDto>(
                "Configuracion.sp_ObtenerConfiguracion", commandType: CommandType.StoredProcedure);
        }

        // dto.LogoRuta ya trae la ruta relativa correcta a guardar: el
        // llamador es responsable de conservar la ruta actual si el usuario
        // no cambió el logo (Sistemas.Core.Files.FileStorageService.Guardar
        // solo se llama cuando sí hay un archivo nuevo).
        public static async Task<(bool Exito, string Mensaje)> GuardarAsync(ConfiguracionDto dto, int usuarioId)
        {
            using var conn = ConnectionFactory.CreateConnection();
            return await conn.QueryFirstAsync<(bool Exito, string Mensaje)>(
                "Configuracion.sp_GuardarConfiguracion",
                new
                {
                    dto.NombreComercial,
                    dto.RTN,
                    dto.Direccion,
                    dto.Telefono,
                    dto.CorreoContacto,
                    dto.LogoRuta,
                    dto.FacturacionLegalActiva,
                    UsuarioId = usuarioId
                },
                commandType: CommandType.StoredProcedure);
        }
    }
}
