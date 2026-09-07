using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows.Forms;

namespace Sistemas.Licencias
{
    // Herramienta interna del VENDEDOR (no se distribuye a clientes): genera
    // una clave de activación firmada a partir del código de máquina que el
    // cliente copia desde la pantalla de Activación de SistemasHN. La llave
    // privada (clave_privada.pem) es el secreto más importante de todo el
    // sistema de licenciamiento — nunca debe subirse a un repositorio público
    // ni distribuirse junto con la app.
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Console.OutputEncoding = Encoding.UTF8;
            Console.WriteLine("=== Generador de claves de activación — SistemasHN ===");
            Console.WriteLine();

            string privadaPem;
            try
            {
                privadaPem = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "clave_privada.pem"));
            }
            catch (Exception ex)
            {
                Console.WriteLine("No se pudo leer clave_privada.pem junto al ejecutable: " + ex.Message);
                return;
            }

            Console.Write("Código de máquina del cliente: ");
            var codigoMaquina = Console.ReadLine()?.Trim() ?? string.Empty;
            if (codigoMaquina.Length == 0)
            {
                Console.WriteLine("El código de máquina no puede estar vacío.");
                return;
            }

            Console.Write("Vigencia en días (Enter = sin vencimiento): ");
            var diasTexto = Console.ReadLine()?.Trim();
            DateTime? expiracion = null;
            if (!string.IsNullOrEmpty(diasTexto))
            {
                if (!int.TryParse(diasTexto, out var dias) || dias <= 0)
                {
                    Console.WriteLine("Los días deben ser un número entero positivo.");
                    return;
                }
                expiracion = DateTime.UtcNow.AddDays(dias);
            }

            var payloadJson = JsonSerializer.Serialize(new { HardwareFingerprint = codigoMaquina, ExpirationUtc = expiracion });
            var payloadBytes = Encoding.UTF8.GetBytes(payloadJson);

            using var rsa = RSA.Create();
            rsa.ImportFromPem(privadaPem);
            var firma = rsa.SignData(payloadBytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);

            var claveActivacion = Convert.ToBase64String(payloadBytes) + "." + Convert.ToBase64String(firma);

            Console.WriteLine();
            Console.WriteLine(expiracion.HasValue
                ? $"Clave generada (vence {expiracion:yyyy-MM-dd}):"
                : "Clave generada (sin vencimiento):");
            Console.WriteLine();
            Console.WriteLine(claveActivacion);
            Console.WriteLine();

            try
            {
                Clipboard.SetText(claveActivacion);
                Console.WriteLine("(Copiada al portapapeles)");
            }
            catch
            {
                // Portapapeles no disponible: no es crítico, la clave ya se imprimió arriba.
            }
        }
    }
}
