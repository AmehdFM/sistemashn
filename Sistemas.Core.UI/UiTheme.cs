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

        // No había ningún rol de aviso (solo Éxito/Error) — se agrega para
        // los casos que no son un error pero tampoco un éxito (crédito por
        // vencer, stock cerca del mínimo).
        public static readonly Color Advertencia = ColorTranslator.FromHtml("#9A6A00");
        public static readonly Color AdvertenciaFondo = ColorTranslator.FromHtml("#FDF3DC");

        // Selección de fila en grillas: mezcla de Primario al 12% sobre
        // blanco. Nunca texto blanco sobre un fondo de acento sólido — ver
        // GridStyler.Aplicar.
        public static readonly Color SeleccionFila = ColorTranslator.FromHtml("#F1E5E7");

        public static readonly Font FuenteBase = new("Segoe UI", 9.5f);
        public static readonly Font FuenteTitulo = new("Segoe UI Semibold", 15f);
        public static readonly Font FuenteGlyph = new("Segoe MDL2 Assets", 14f);

        // Escala de espaciado 4/8px de la guía UI/UX — reemplaza los
        // números sueltos (12, 16, 24...) repetidos en cada pantalla.
        public static class Espacio
        {
            public const int Xxs = 2;
            public const int Xs = 4;
            public const int Sm = 8;
            public const int Md = 12;
            public const int Lg = 16;
            public const int Xl = 24;
            public const int Xxl = 32;
            public const int Huge = 48;
        }

        // Alturas/anchos de referencia para densidad "Normal" (guía §4).
        // No incluye el ancho del sidebar: ese lo fija ADR-0010 (220/56px)
        // y no se toca acá.
        public static class Medidas
        {
            public const int AlturaControl = 30;
            public const int AlturaFila = 28;
            public const int AlturaEncabezadoFila = 32;
            public const int AlturaBarraHerramientas = 48;
            public const int AlturaBarraEstado = 24;
            public const int AnchoMaximoFormulario = 760;
        }
    }
}
