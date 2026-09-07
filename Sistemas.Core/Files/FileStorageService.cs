using System;
using System.IO;

namespace Sistemas.Core.Files
{
    // Almacén de archivos genérico y reutilizable: hoy lo usa solo el logo
    // del negocio, pero está pensado desde el inicio para cualquier imagen
    // futura (fotos de producto, comprobantes, etc.) — basta con darle su
    // propia "categoria" para tener su propia carpeta.
    //
    // Los archivos NO viven en la base de datos: solo se guarda la ruta
    // relativa (ej. "Logos/3f2a....png") en la columna correspondiente, y
    // esta clase resuelve esa ruta contra la carpeta compartida a nivel de
    // máquina — la misma idea que ya usa ConnectionFactory para
    // appsettings.json, para que todas las verticales instaladas en la
    // misma PC compartan un solo almacén.
    public static class FileStorageService
    {
        private static string CarpetaBase => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "SistemasHN", "Archivos");

        // Devuelve la ruta RELATIVA (la que se guarda en la base de datos),
        // no la ruta absoluta en disco.
        public static string Guardar(string categoria, byte[] contenido, string extension)
        {
            var carpetaCategoria = Path.Combine(CarpetaBase, categoria);
            Directory.CreateDirectory(carpetaCategoria);

            if (!extension.StartsWith('.')) extension = "." + extension;
            var nombreArchivo = Guid.NewGuid().ToString("N") + extension;

            File.WriteAllBytes(Path.Combine(carpetaCategoria, nombreArchivo), contenido);
            return Path.Combine(categoria, nombreArchivo);
        }

        public static byte[]? Leer(string? rutaRelativa)
        {
            if (string.IsNullOrWhiteSpace(rutaRelativa)) return null;
            var rutaCompleta = Path.Combine(CarpetaBase, rutaRelativa);
            return File.Exists(rutaCompleta) ? File.ReadAllBytes(rutaCompleta) : null;
        }

        // No falla si el archivo ya no existe: reemplazar un logo por otro
        // no debe romperse porque el anterior se perdió por fuera del sistema.
        public static void Eliminar(string? rutaRelativa)
        {
            if (string.IsNullOrWhiteSpace(rutaRelativa)) return;
            var rutaCompleta = Path.Combine(CarpetaBase, rutaRelativa);
            if (File.Exists(rutaCompleta)) File.Delete(rutaCompleta);
        }
    }
}
