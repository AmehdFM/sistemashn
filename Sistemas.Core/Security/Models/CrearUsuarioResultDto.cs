namespace Sistemas.Core.Security.Models
{
    // Mapea 1:1 el result set de Security.sp_CrearUsuario.
    internal sealed class CrearUsuarioResultDto
    {
        public bool Exito { get; set; }
        public string Mensaje { get; set; } = string.Empty;
        public int? UsuarioId { get; set; }
    }
}
