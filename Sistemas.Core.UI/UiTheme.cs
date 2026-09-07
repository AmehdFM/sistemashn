using System.Drawing;

namespace Sistemas.Core.UI
{
    // Paleta mínima compartida entre las pantallas de Core, para no repetir
    // colores sueltos en cada Form.
    public static class UiTheme
    {
        // Paleta "Grafito y Vino": grafito neutro (sin sesgo azul) con un
        // rojo vino apagado como acento — elegida entre 5 opciones estilo
        // enterprise para diferenciarse del "azul de software" genérico sin
        // dejar de ser sobria.
        public static readonly Color Primario = ColorTranslator.FromHtml("#8B2635");
        public static readonly Color PrimarioOscuro = ColorTranslator.FromHtml("#6E1E2A");
        public static readonly Color SidebarFondo = ColorTranslator.FromHtml("#27272A");
        public static readonly Color SidebarFondoActivo = ColorTranslator.FromHtml("#38383D");
        public static readonly Color SidebarTexto = ColorTranslator.FromHtml("#E7E5E4");
        public static readonly Color SidebarTextoTenue = ColorTranslator.FromHtml("#A3A09C");
        public static readonly Color FondoContenido = ColorTranslator.FromHtml("#FAFAF9");
        public static readonly Color TextoOscuro = ColorTranslator.FromHtml("#27272A");
        public static readonly Color TextoTenue = ColorTranslator.FromHtml("#6B6864");
        public static readonly Color Exito = ColorTranslator.FromHtml("#2F7D4F");
        public static readonly Color Error = ColorTranslator.FromHtml("#C0362C");
        public static readonly Color ErrorFondo = ColorTranslator.FromHtml("#FEE2E2");
        public static readonly Color Borde = ColorTranslator.FromHtml("#E4E1DC");

        public static readonly Font FuenteBase = new("Segoe UI", 9.5f);
        public static readonly Font FuenteTitulo = new("Segoe UI Semibold", 15f);
        public static readonly Font FuenteGlyph = new("Segoe MDL2 Assets", 14f);
    }
}
