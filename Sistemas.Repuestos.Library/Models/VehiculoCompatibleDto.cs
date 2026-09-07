namespace Sistemas.Repuestos.Library.Models
{
    public sealed class VehiculoCompatibleDto
    {
        public string Marca { get; set; } = string.Empty;
        public string Modelo { get; set; } = string.Empty;
        public int AnioDesde { get; set; }
        public int AnioHasta { get; set; }
    }
}
