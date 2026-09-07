using System;

namespace Sistemas.Repuestos.Library.Models
{
    // Mapea Repuestos.sp_ListarVentas.
    public sealed class VentaDto
    {
        public int Id { get; set; }
        public string NumeroFactura { get; set; } = string.Empty;
        public DateTime Fecha { get; set; }
        public decimal Subtotal { get; set; }
        public decimal MontoISV { get; set; }
        public decimal Total { get; set; }
        public bool EsCredito { get; set; }
        public bool Anulada { get; set; }
        public int UsuarioId { get; set; }
    }
}
