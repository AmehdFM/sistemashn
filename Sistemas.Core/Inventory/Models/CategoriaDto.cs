namespace Sistemas.Core.Inventory.Models
{
    public sealed class CategoriaDto
    {
        public int Id { get; set; }
        public string Nombre { get; set; } = string.Empty;
        public int? CategoriaPadreId { get; set; }
    }
}
