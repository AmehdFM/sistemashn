using System.Reflection;

namespace Sistemas.Core.UI
{
    public static class BrandingAssets
    {
        private static Image? _logoCreador;
        private static Icon? _iconoApp;

        public static Image LogoCreador => _logoCreador ??= CargarLogoCreador();

        public static Icon IconoApp => _iconoApp ??= CargarIconoApp();

        private static Image CargarLogoCreador()
        {
            var assembly = Assembly.GetExecutingAssembly();
            var stream = assembly.GetManifestResourceStream("Sistemas.Core.UI.Assets.elements_logo.png")
                ?? throw new InvalidOperationException("No se encontró el recurso embebido del logo de Elements System.");
            // No se dispersa el stream: GDI+ puede decodificar la imagen de
            // forma diferida y necesita el stream vivo mientras la Image
            // esté en uso.
            return Image.FromStream(stream);
        }

        private static Icon CargarIconoApp()
        {
            var assembly = Assembly.GetExecutingAssembly();
            var stream = assembly.GetManifestResourceStream("Sistemas.Core.UI.Assets.elements_logo.ico")
                ?? throw new InvalidOperationException("No se encontró el recurso embebido del icono de Elements System.");
            return new Icon(stream);
        }
    }
}
