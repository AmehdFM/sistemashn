using System;

namespace Sistemas.Core.Security
{
    // Singleton estático: es una app de escritorio de un solo usuario por
    // proceso, no hace falta nada más elaborado para guardar la sesión activa.
    public sealed class SessionContext
    {
        public int UsuarioId { get; }
        public string NombreUsuario { get; }
        public string NombreCompleto { get; }
        public int RolId { get; }
        public string NombreRol { get; }

        public SessionContext(int usuarioId, string nombreUsuario, string nombreCompleto, int rolId, string nombreRol)
        {
            UsuarioId = usuarioId;
            NombreUsuario = nombreUsuario;
            NombreCompleto = nombreCompleto;
            RolId = rolId;
            NombreRol = nombreRol;
        }

        public bool EsAdministrador => string.Equals(NombreRol, "Administrador", StringComparison.OrdinalIgnoreCase);

        public static SessionContext? Current { get; private set; }

        public static void Iniciar(SessionContext sesion) => Current = sesion;

        public static void Cerrar() => Current = null;
    }
}
