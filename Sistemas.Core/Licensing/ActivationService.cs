using System;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Sistemas.Core.Licensing
{
    internal class ActivationService
    {
        // Public key PEM (RSA) used to verify signatures. Reemplazar por la clave pública real del vendedor.
        private const string PublicKeyPem = @"-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAw7oZ1q2jQK0xVxR2bV7y
2m3x0bqvA3GZkq1b5u8Jm7C3rQGg1c2qv3x8Yv9z1wQGvZQKz6wQ3b2K8xQe7u6G
6b9x1wQK1zqv3y8bGzQ6V8wQ2z3K9v1xQKz6wQ3b2K8xQe7u6G6b9x1wQK1zqv3y
8bGzQ6V8wQ2z3K9v1xQKz6wQ3b2K8xQe7u6G6b9x1wQK1zqv3y8bGzQ6V8wQ2z3K
9v1xQKz6wQ3b2K8xQe7u6G6b9x1wQK1zqv3y8bGzQ6V8wQ2z3K9v1xQIDAQAB
-----END PUBLIC KEY-----";

        // Genera fingerprint hardware
        public static string GetHardwareFingerprint() => MachineIdHelper.GetHardwareFingerprint();

        // Validar clave de activación (formato: base64(payload).base64(signature))
        public static bool ValidateActivationKey(string activationKey, out string message)
        {
            message = string.Empty;
            if (string.IsNullOrWhiteSpace(activationKey))
            {
                message = "Clave vacía";
                return false;
            }

            var parts = activationKey.Split('.', 2);
            if (parts.Length != 2)
            {
                message = "Formato de clave inválido";
                return false;
            }

            try
            {
                var payloadBytes = Convert.FromBase64String(parts[0]);
                var sigBytes = Convert.FromBase64String(parts[1]);

                // verify signature
                using var rsa = RSA.Create();
                rsa.ImportFromPem(PublicKeyPem.ToCharArray());
                bool validSig = rsa.VerifyData(payloadBytes, sigBytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
                if (!validSig)
                {
                    message = "Firma inválida";
                    return false;
                }

                var payloadJson = Encoding.UTF8.GetString(payloadBytes);
                var payload = JsonSerializer.Deserialize<LicensePayload>(payloadJson);
                if (payload == null)
                {
                    message = "Payload inválido";
                    return false;
                }

                var currentFp = GetHardwareFingerprint();
                if (!string.Equals(currentFp, payload.HardwareFingerprint, StringComparison.OrdinalIgnoreCase))
                {
                    message = "La clave no pertenece a esta máquina";
                    return false;
                }

                if (payload.ExpirationUtc.HasValue && DateTime.UtcNow > payload.ExpirationUtc.Value)
                {
                    message = "La licencia ha expirado";
                    return false;
                }

                // todo: almacenar de forma segura
                LicenseStore.SaveEncrypted(activationKey);
                message = "Licencia válida";
                return true;
            }
            catch (FormatException)
            {
                message = "Contenido de la clave no es Base64 válido";
                return false;
            }
            catch (CryptographicException)
            {
                message = "Error criptográfico verificando la clave";
                return false;
            }
            catch (Exception ex)
            {
                message = "Error validando la clave: " + ex.Message;
                return false;
            }
        }

        // Cargar y validar clave guardada
        public static bool TryLoadSavedLicense(out string message)
        {
            message = string.Empty;
            var saved = LicenseStore.LoadDecrypted();
            if (string.IsNullOrWhiteSpace(saved))
            {
                message = "No hay licencia guardada";
                return false;
            }
            return ValidateActivationKey(saved, out message);
        }
    }
}
