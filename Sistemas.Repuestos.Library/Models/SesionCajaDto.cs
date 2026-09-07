using System;

namespace Sistemas.Repuestos.Library.Models
{
    // Mapea Repuestos.sp_ObtenerSesionCajaAbierta / sp_ListarSesionesCaja.
    public sealed class SesionCajaDto
    {
        public int Id { get; set; }
        public int UsuarioAperturaId { get; set; }
        public string? UsuarioAperturaNombre { get; set; }
        public DateTime FechaApertura { get; set; }
        public decimal MontoApertura { get; set; }
        public int? UsuarioCierreId { get; set; }
        public string? UsuarioCierreNombre { get; set; }
        public DateTime? FechaCierre { get; set; }
        public decimal? MontoCierreDeclarado { get; set; }
        public decimal? MontoCierreCalculado { get; set; }
        public decimal? Diferencia { get; set; }
        public string Estado { get; set; } = string.Empty;
    }
}
