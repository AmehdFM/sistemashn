using System;

namespace Sistemas.Core.Facturacion.Models
{
    public sealed class ConfiguracionCaiDto
    {
        public bool Existe { get; set; }
        public string? RangoAutorizado { get; set; }
        public string? RangoInicial { get; set; }
        public string? RangoFinal { get; set; }
        public string? CorrelativoActual { get; set; }
        public DateTime? FechaAutorizacion { get; set; }
        public DateTime? FechaVencimiento { get; set; }
    }
}
