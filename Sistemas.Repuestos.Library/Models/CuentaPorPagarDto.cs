using System;

namespace Sistemas.Repuestos.Library.Models
{
    public sealed class CuentaPorPagarDto
    {
        public int Id { get; set; }
        public int CompraId { get; set; }
        public string? NumeroFacturaProveedor { get; set; }
        public decimal MontoOriginal { get; set; }
        public decimal SaldoPendiente { get; set; }
        public DateTime FechaVencimiento { get; set; }
        public string Estado { get; set; } = string.Empty;
        public bool EstaVencida { get; set; }
    }
}
