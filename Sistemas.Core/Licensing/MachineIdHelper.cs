using System;
using System.Management;
using System.Security.Cryptography;
using System.Text;

namespace Sistemas.Core.Licensing
{
    internal static class MachineIdHelper
    {
        // Devuelve un fingerprint SHA256 (hex) construido a partir de CPU|Disk|Baseboard
        public static string GetHardwareFingerprint()
        {
            string cpu = GetWmiProperty("Win32_Processor", "ProcessorId");
            string disk = GetWmiProperty("Win32_PhysicalMedia", "SerialNumber");
            if (string.IsNullOrWhiteSpace(disk)) // fallback
                disk = GetWmiProperty("Win32_DiskDrive", "SerialNumber");
            string baseboard = GetWmiProperty("Win32_BaseBoard", "SerialNumber");

            string raw = string.Join("|", new[] { cpu, disk, baseboard });
            if (string.IsNullOrWhiteSpace(raw)) raw = Environment.MachineName;

            using var sha = SHA256.Create();
            var bytes = Encoding.UTF8.GetBytes(raw);
            var hash = sha.ComputeHash(bytes);
            return BitConverter.ToString(hash).Replace("-", "");
        }

        private static string GetWmiProperty(string wmiClass, string property)
        {
            try
            {
                using var search = new ManagementObjectSearcher($"SELECT {property} FROM {wmiClass}");
                foreach (ManagementObject obj in search.Get())
                {
                    try
                    {
                        var val = obj[property];
                        if (val != null)
                        {
                            var s = val.ToString().Trim();
                            if (!string.IsNullOrWhiteSpace(s)) return s;
                        }
                    }
                    catch { }
                }
            }
            catch { }
            return string.Empty;
        }
    }
}
