using System.Collections.Generic;

namespace Sistemas.Core.Inventory.Models
{
    // Mapea el primer result set de Inventario.sp_ImportarProductosMasivo.
    public sealed class ResultadoImportacionDto
    {
        public bool Exito { get; set; }
        public string Mensaje { get; set; } = string.Empty;
        public int FilasExitosas { get; set; }
        public int FilasFallidas { get; set; }
        public List<DetalleImportacionDto> Detalle { get; set; } = new();
    }
}
