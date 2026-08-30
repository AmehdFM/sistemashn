using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace Sistemas.Core.Licensing
{
    internal static class LicenseStore
    {
        private static string GetPath()
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SistemasHN");
            Directory.CreateDirectory(dir);
            return Path.Combine(dir, "license.dat");
        }

        public static void SaveEncrypted(string activationPayload)
        {
            var path = GetPath();
            var data = Encoding.UTF8.GetBytes(activationPayload);
            var protectedBytes = ProtectedData.Protect(data, null, DataProtectionScope.LocalMachine);
            File.WriteAllBytes(path, protectedBytes);
        }

        public static string? LoadDecrypted()
        {
            var path = GetPath();
            if (!File.Exists(path)) return null;
            try
            {
                var protectedBytes = File.ReadAllBytes(path);
                var data = ProtectedData.Unprotect(protectedBytes, null, DataProtectionScope.LocalMachine);
                return Encoding.UTF8.GetString(data);
            }
            catch
            {
                return null;
            }
        }

        public static void Delete()
        {
            var path = GetPath();
            try { if (File.Exists(path)) File.Delete(path); } catch { }
        }
    }
}
