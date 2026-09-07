namespace Sistemas.Repuestos.Library.Models
{
    // Mapea Repuestos.sp_CompararPreciosProveedor.
    public sealed class PrecioProveedorDto
    {
        public int ProveedorId { get; set; }
        public string Nombre { get; set; } = string.Empty;
        public string? Telefono { get; set; }
        public decimal PrecioCompra { get; set; }
    }
}
