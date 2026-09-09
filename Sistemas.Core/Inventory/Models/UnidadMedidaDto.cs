namespace Sistemas.Core.Inventory.Models
{
    // Mapea 1:1 el result set de Inventario.sp_ListarUnidadesMedida.
    public sealed class UnidadMedidaDto
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public string Simbolo { get; set; } = string.Empty;
        public bool PermiteFraccion { get; set; }
        public string? Sistema { get; set; }
        public bool Activo { get; set; }
    }
}
