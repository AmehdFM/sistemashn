namespace Sistemas.Core
{
    // Único lugar donde viven los textos de la capa de negocio compartida
    // (login, licencia, exportación a Excel). Los textos específicos de cada
    // vertical NO van aquí — Core no debe conocer nada de una vertical en
    // particular (mismo principio que ya sigue IVerticalModuleProvider).
    // Cada proyecto de nivel superior tiene su propio Textos.cs:
    // Sistemas.Core.UI/Textos.cs (pantallas compartidas) y
    // Sistemas.Repuestos.Library/Textos.cs (pantallas de esa vertical).
    public static class Textos
    {
        public static class Auth
        {
            public const string UsuarioOPasswordIncorrectos = "Usuario o contraseña incorrectos";
            public const string InicioSesionExitoso = "Inicio de sesión exitoso";
        }

        public static class Licencia
        {
            public const string ClaveVacia = "Clave vacía";
            public const string FormatoInvalido = "Formato de clave inválido";
            public const string FirmaInvalida = "Firma inválida";
            public const string PayloadInvalido = "Payload inválido";
            public const string NoPerteneceAEstaMaquina = "La clave no pertenece a esta máquina";
            public const string LicenciaExpirada = "La licencia ha expirado";
            public const string LicenciaValida = "Licencia válida";
            public const string NoHayLicenciaGuardada = "No hay licencia guardada";
            public const string ContenidoNoEsBase64 = "Contenido de la clave no es Base64 válido";
            public const string ErrorCriptografico = "Error criptográfico verificando la clave";
            public const string ErrorValidandoPrefijo = "Error validando la clave: ";
        }

        public static class Excel
        {
            public const string ColumnaNoCoincideFormato =
                "La columna {0} debería llamarse '{1}' pero dice '{2}'. " +
                "Descargue la plantilla y no cambie el orden ni el nombre de las columnas.";
        }
    }
}
