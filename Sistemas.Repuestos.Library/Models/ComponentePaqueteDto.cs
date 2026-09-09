namespace Sistemas.Repuestos.Library.Models
{
    public sealed class ComponentePaqueteDto
    {
        public int ComponenteProductoId { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public decimal Cantidad { get; set; }
        public bool PermiteFraccion { get; set; } = true;
    }
}
