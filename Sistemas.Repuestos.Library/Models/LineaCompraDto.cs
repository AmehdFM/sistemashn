namespace Sistemas.Repuestos.Library.Models
{
    // Una línea de la grilla de captura de Repuestos.sp_RegistrarCompra
    // (se arma como Repuestos.CompraDetalleTableType al enviarla).
    public sealed class LineaCompraDto
    {
        public int ProductoId { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public int Cantidad { get; set; }
        public decimal CostoUnitario { get; set; }
        public decimal Subtotal => Cantidad * CostoUnitario;
    }
}
