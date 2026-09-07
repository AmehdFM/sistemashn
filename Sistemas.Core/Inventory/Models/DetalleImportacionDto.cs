namespace Sistemas.Core.Inventory.Models
{
    // Mapea el segundo result set de Inventario.sp_ImportarProductosMasivo:
    // una fila por cada línea del Excel importado.
    public sealed class DetalleImportacionDto
    {
        public string Codigo { get; set; } = string.Empty;
        public bool Exito { get; set; }
        public string Mensaje { get; set; } = string.Empty;
        public string? Accion { get; set; } // "INSERT" / "UPDATE" / null si falló
    }
}
