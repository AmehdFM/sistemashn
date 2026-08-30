using System;

namespace Sistemas.Core.Licensing
{
    internal class LicensePayload
    {
        public string HardwareFingerprint { get; set; }
        public DateTime? ExpirationUtc { get; set; }
    }
}
