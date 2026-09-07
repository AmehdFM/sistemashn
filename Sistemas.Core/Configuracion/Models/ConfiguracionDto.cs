using System;

namespace Sistemas.Core.Configuracion.Models
{
    public sealed class ConfiguracionDto
    {
        public bool Existe { get; set; }
        public string? NombreComercial { get; set; }
        public string? RTN { get; set; }
        public string? Direccion { get; set; }
        public string? Telefono { get; set; }
        public string? CorreoContacto { get; set; }
        public string? LogoRuta { get; set; }
        public bool FacturacionLegalActiva { get; set; }
        public DateTime? FechaActualizacion { get; set; }
    }
}
