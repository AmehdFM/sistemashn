using System;
using System.Data;
using System.IO;
using System.Linq;
using System.Text.Json;
using Microsoft.Data.SqlClient;

namespace Sistemas.Core.Data
{
    // Todas las verticales instaladas en la misma máquina apuntan a la misma
    // base de datos, así que el connection string vive en una ubicación
    // compartida a nivel de máquina (ProgramData), no junto a cada .exe.
    // En desarrollo, si ese archivo no existe, se usa el que esté junto al
    // ejecutable para no tener que tocar ProgramData en cada F5.
    public static class ConnectionFactory
    {
        private static readonly Lazy<string> _connectionString = new(LoadConnectionString);

        public static IDbConnection CreateConnection()
        {
            var connection = new SqlConnection(_connectionString.Value);
            connection.Open();
            return connection;
        }

        private static string LoadConnectionString()
        {
            var candidatos = new[]
            {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "SistemasHN", "appsettings.json"),
                Path.Combine(AppContext.BaseDirectory, "appsettings.json")
            };

            var rutaConfig = candidatos.FirstOrDefault(File.Exists)
                ?? throw new FileNotFoundException(
                    "No se encontró appsettings.json en ProgramData\\SistemasHN ni junto al ejecutable.");

            using var doc = JsonDocument.Parse(File.ReadAllText(rutaConfig));
            var cs = doc.RootElement.GetProperty("ConnectionStrings").GetProperty("Default").GetString();

            return string.IsNullOrWhiteSpace(cs)
                ? throw new InvalidOperationException($"ConnectionStrings:Default vacío en {rutaConfig}")
                : cs;
        }
    }
}
