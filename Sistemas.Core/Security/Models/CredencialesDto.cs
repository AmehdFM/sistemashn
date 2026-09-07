namespace Sistemas.Core.Security.Models
{
    // Mapea 1:1 el result set de Security.sp_ObtenerCredencialesLogin.
    internal sealed class CredencialesDto
    {
        public bool Exito { get; set; }
        public int? UsuarioId { get; set; }
        public string? PasswordHash { get; set; }
        public string? NombreCompleto { get; set; }
        public int? RolId { get; set; }
        public string? NombreRol { get; set; }
    }
}
