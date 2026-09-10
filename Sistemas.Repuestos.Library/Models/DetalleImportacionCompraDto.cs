namespace Sistemas.Repuestos.Library.Models
{
    // Una fila por cada grupo Proveedor+NumeroFacturaProveedor procesado al
    // importar compras desde Excel — no es DetalleImportacionDto de
    // Sistemas.Core.Inventory.Models porque esa vive en otra capa/dominio
    // (importación de productos, no de compras).
    public sealed class DetalleImportacionCompraDto
    {
        public string Identificador { get; set; } = string.Empty; // "Proveedor — NumFactura"
        public bool Exito { get; set; }
        public string Mensaje { get; set; } = string.Empty;
        public int CantidadLineas { get; set; }
    }
}
