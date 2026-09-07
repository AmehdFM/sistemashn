using System;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Sistemas.Core.Licensing
{
    public class ActivationService
    {
        // Llave pública RSA real del vendedor — su contraparte privada vive
        // SOLO en Sistemas.Licencias/clave_privada.pem (nunca en un ensamblado
        // que se distribuya a clientes) y es la que firma cada clave de
        // activación.
        private const string PublicKeyPem = @"-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy0SCCCYX4goeaWRiRzNu
qNbeEannQfinsiBJ6FFl4a2NfhoJgHH+sVlk30kuO/HIteV9L9QXOgIzqTRSg+pB
PwZvEsgF5CCOhkTB7hus9k+tinMSGZ3sP2tYptzZN9Y9eaDOLbyxKdFk7KGfDqSO
y5PqG4qSCby44K7/Uqaa9Db1k+0SUjVwJn9heLTBwo4bGdo1r1QI6edjr1cO8GZl
DVJVtebbDJhjNd4mOO/gBADPjm59vTqusmsFSMqoAlnqnDLtyTQ6HekkVfFXuXrk
+pbinhWBwKEGqW+ZVL56X+G4fHxysfJoILMP/OoWx8H+PUPQKWf+eR0YcJeGwf9T
cQIDAQAB
-----END PUBLIC KEY-----";

        // Genera fingerprint hardware
        public static string GetHardwareFingerprint() => MachineIdHelper.GetHardwareFingerprint();

        // Validar clave de activación (formato: base64(payload).base64(signature))
        public static bool ValidateActivationKey(string activationKey, out string message)
        {
            message = string.Empty;
            if (string.IsNullOrWhiteSpace(activationKey))
            {
                message = Textos.Licencia.ClaveVacia;
                return false;
            }

            var parts = activationKey.Split('.', 2);
            if (parts.Length != 2)
            {
                message = Textos.Licencia.FormatoInvalido;
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
                    message = Textos.Licencia.FirmaInvalida;
                    return false;
                }

                var payloadJson = Encoding.UTF8.GetString(payloadBytes);
                var payload = JsonSerializer.Deserialize<LicensePayload>(payloadJson);
                if (payload == null)
                {
                    message = Textos.Licencia.PayloadInvalido;
                    return false;
                }

                var currentFp = GetHardwareFingerprint();
                if (!string.Equals(currentFp, payload.HardwareFingerprint, StringComparison.OrdinalIgnoreCase))
                {
                    message = Textos.Licencia.NoPerteneceAEstaMaquina;
                    return false;
                }

                if (payload.ExpirationUtc.HasValue && DateTime.UtcNow > payload.ExpirationUtc.Value)
                {
                    message = Textos.Licencia.LicenciaExpirada;
                    return false;
                }

                // todo: almacenar de forma segura
                LicenseStore.SaveEncrypted(activationKey);
                message = Textos.Licencia.LicenciaValida;
                return true;
            }
            catch (FormatException)
            {
                message = Textos.Licencia.ContenidoNoEsBase64;
                return false;
            }
            catch (CryptographicException)
            {
                message = Textos.Licencia.ErrorCriptografico;
                return false;
            }
            catch (Exception ex)
            {
                message = Textos.Licencia.ErrorValidandoPrefijo + ex.Message;
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
                message = Textos.Licencia.NoHayLicenciaGuardada;
                return false;
            }
            return ValidateActivationKey(saved, out message);
        }
    }
}
