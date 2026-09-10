using System.Collections.Generic;

namespace Sistemas.Repuestos.Library.Models
{
    // Resumen de CompraService.ImportarDesdeExcelAsync — una compra por
    // grupo Proveedor+NumeroFacturaProveedor, no una fila por línea de
    // Excel (esa granularidad la lleva Detalle[i].CantidadLineas).
    public sealed class ResultadoImportacionComprasDto
    {
        public bool Exito { get; set; }
        public string Mensaje { get; set; } = string.Empty;
        public int ComprasExitosas { get; set; }
        public int ComprasFallidas { get; set; }
        public List<DetalleImportacionCompraDto> Detalle { get; set; } = new();
    }
}
