namespace Sistemas.Repuestos.Library.Models
{
    // Una línea del carrito del POS. Solo ProductoId+Cantidad viajan al
    // servidor (Repuestos.VentaDetalleTableType) — precio y tasa de ISV son
    // valores de REFERENCIA para mostrar un total estimado en pantalla; el
    // valor real y definitivo lo congela Repuestos.sp_RegistrarVenta.
    public sealed class LineaCarritoDto
    {
        public int ProductoId { get; set; }
        public string Codigo { get; set; } = string.Empty;
        public string Nombre { get; set; } = string.Empty;
        public int Cantidad { get; set; }
        public decimal PrecioUnitarioReferencial { get; set; }
        public decimal TasaISVReferencial { get; set; }
        public decimal SubtotalReferencial => Cantidad * PrecioUnitarioReferencial;
    }
}
