namespace Sistemas.Repuestos.Library.Models
{
    // Mapea Repuestos.sp_BuscarPorEquivalencia.
    public sealed class EquivalenciaResultadoDto
    {
        public int Id { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public decimal PrecioUnitario { get; set; }
        public decimal TasaISV { get; set; }
        public int StockActual { get; set; }
        public bool Activo { get; set; }
        public string NumeroCoincidente { get; set; } = string.Empty;
        public string Origen { get; set; } = string.Empty;
    }
}
