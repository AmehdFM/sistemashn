using System;

namespace Sistemas.Core.Inventory.Models
{
    // Mapea 1:1 el result set de Inventario.sp_ListarProductos.
    public sealed class ProductoDto
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public string? Descripcion { get; set; }
        public decimal PrecioUnitario { get; set; }
        public int? CategoriaId { get; set; }
        public string? NombreCategoria { get; set; }
        public decimal TasaISV { get; set; }
        public decimal StockActual { get; set; }
        public decimal StockMinimo { get; set; }
        public int UnidadMedidaId { get; set; }
        public string? UnidadMedidaCodigo { get; set; }
        public string? UnidadMedidaSimbolo { get; set; }
        public bool PermiteFraccionUnidad { get; set; }
        public bool Activo { get; set; }
        public DateTime FechaCreacion { get; set; }
    }
}
