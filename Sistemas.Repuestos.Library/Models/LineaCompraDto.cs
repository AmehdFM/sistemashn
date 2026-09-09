namespace Sistemas.Repuestos.Library.Models
{
    // Una línea de la grilla de captura de Repuestos.sp_RegistrarCompra
    // (se arma como Repuestos.CompraDetalleTableType al enviarla).
    public sealed class LineaCompraDto
    {
        public int ProductoId { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public decimal Cantidad { get; set; }
        public bool PermiteFraccion { get; set; } = true;
        public decimal CostoUnitario { get; set; }
        public decimal Subtotal => Cantidad * CostoUnitario;
    }
}
