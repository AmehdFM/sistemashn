using System.Collections.Generic;

namespace Sistemas.Repuestos.Library.Models
{
    // Mapea los 3 result sets de Repuestos.sp_ObtenerProductoRepuesto.
    public sealed class RepuestoDetalleDto
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public string? Descripcion { get; set; }
        public decimal PrecioUnitario { get; set; }
        public int? CategoriaId { get; set; }
        public decimal TasaISV { get; set; }
        public decimal StockActual { get; set; }
        public decimal StockMinimo { get; set; }
        public bool Activo { get; set; }
        public string? NumeroParte { get; set; }
        public string? MarcaFabricante { get; set; }
        public bool? EsOriginal { get; set; }

        public List<VehiculoCompatibleDto> Vehiculos { get; set; } = new();
        public List<NumeroEquivalenteDto> Equivalentes { get; set; } = new();
    }
}
