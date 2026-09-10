namespace Sistemas.Repuestos.Library.Models
{
    // Mapea Repuestos.Terceros — un usuario externo (no empleado) con el
    // que se tiene una relación comercial. Un tercero puede ser proveedor,
    // cliente, o ambos a la vez (EsProveedor/EsCliente independientes).
    public sealed class TerceroDto
    {
        public int Id { get; set; }
        public string Nombre { get; set; } = string.Empty;
        public string? Empresa { get; set; }
        public string? Correo { get; set; }
        public string? Telefono { get; set; }
        public string? RTN { get; set; }
        public bool EsProveedor { get; set; }
        public bool EsCliente { get; set; }
        public bool Activo { get; set; }
    }
}
