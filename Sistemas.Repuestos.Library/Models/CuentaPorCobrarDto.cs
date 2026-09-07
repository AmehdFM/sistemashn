using System;

namespace Sistemas.Repuestos.Library.Models
{
    public sealed class CuentaPorCobrarDto
    {
        public int Id { get; set; }
        public int VentaId { get; set; }
        public string NumeroFactura { get; set; } = string.Empty;
        public decimal MontoOriginal { get; set; }
        public decimal SaldoPendiente { get; set; }
        public DateTime FechaVencimiento { get; set; }
        public string Estado { get; set; } = string.Empty;
        public bool EstaVencida { get; set; }
    }
}
