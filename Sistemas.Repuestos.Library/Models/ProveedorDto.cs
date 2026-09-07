namespace Sistemas.Repuestos.Library.Models
{
    public sealed class ProveedorDto
    {
        public int Id { get; set; }
        public string Nombre { get; set; } = string.Empty;
        public string? RTN { get; set; }
        public string? Telefono { get; set; }
        public string? Contacto { get; set; }
        public bool Activo { get; set; }
    }
}
