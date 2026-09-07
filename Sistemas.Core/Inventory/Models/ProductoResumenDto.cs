namespace Sistemas.Core.Inventory.Models
{
    // Fila resumida de Inventario.sp_BuscarProductosPorCodigos, usada solo
    // para resolver códigos en lote (ej. importación de compras desde
    // Excel en Sistemas.Repuestos.Library). Vive dentro de un
    // Dictionary<string, ProductoResumenDto> que se arma y se descarta
    // dentro de un método, nunca se bindea a ningún control — por eso va
    // como readonly record struct y no como clase (ver
    // LINEAMIENTOS_RENDIMIENTO.md).
    public readonly record struct ProductoResumenDto(int Id, string Codigo, string Nombre, decimal PrecioUnitario);
}
