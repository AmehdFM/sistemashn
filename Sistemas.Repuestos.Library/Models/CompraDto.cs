using System;

namespace Sistemas.Repuestos.Library.Models
{
    // Mapea Repuestos.sp_ListarCompras.
    public sealed class CompraDto
    {
        public int Id { get; set; }
        public DateTime Fecha { get; set; }
        public int ProveedorId { get; set; }
        public string NombreProveedor { get; set; } = string.Empty;
        public string? NumeroFacturaProveedor { get; set; }
        public decimal Total { get; set; }
        public bool EsCredito { get; set; }
        public int UsuarioId { get; set; }
    }
}
