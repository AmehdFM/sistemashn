namespace Sistemas.Core.UI
{
    // Único lugar donde viven los textos de las pantallas COMPARTIDAS por
    // cualquier vertical (arranque, dashboard, ajustes). Los textos propios
    // de una vertical (Repuestos, y las que sigan) NO van aquí — cada una
    // tiene su propio Textos.cs, igual que Sistemas.Core tiene el suyo para
    // la capa de negocio compartida.
    public static class Textos
    {
        // Textos genéricos de UI reutilizados por varias pantallas: títulos
        // de diálogo, prefijos de error de conexión, controles de listado.
        public static class Comun
        {
            public const string TituloError = "Error";
            public const string TituloInformacion = "Información";
            public const string TituloConfirmar = "Confirmar";
            public const string NoSeConectoBdPrefijo = "No se pudo conectar con la base de datos: ";
            public const string NoSeGuardoPrefijo = "No se pudo guardar: ";
            public const string NoSeCargoImagenPrefijo = "No se pudo cargar la imagen: ";
            public const string FiltroImagenes = "Imágenes (*.png;*.jpg;*.jpeg;*.bmp)|*.png;*.jpg;*.jpeg;*.bmp";
            public const string TituloSeleccionarLogo = "Seleccionar logo del negocio";

            public const string BotonAnterior = "< Anterior";
            public const string BotonSiguiente = "Siguiente >";
            public const string FormatoPaginacion = "Página {0} de {1}  ·  {2} fila(s)";

            // Los 4 estados obligatorios de toda lista (guía UI/UX §9.6).
            public const string EstadoCargando = "Cargando...";
            public const string BotonLimpiarFiltros = "Limpiar filtros";
            public const string BotonReintentar = "Reintentar";
        }

        public static class Dashboard
        {
            public const string ModuloMenu = "Menú";
            public const string ModuloAjustes = "Ajustes";
            public const string ConfirmarCerrarSesion = "¿Desea cerrar la sesión?";
            public const string BotonCerrarSesion = "Cerrar sesión";

            public const string AjustesTitulo = "Ajustes de la empresa";
            public const string TabGeneral = "General";
            public const string TabFacturacion = "Facturación";
            public const string TabUsuarios = "Usuarios";
            public const string CampoRequiereFacturacionLegal = "Requiere facturación legal (CAI)";
            public const string BotonConfigurarCai = "Configurar CAI";
            public const string TituloConfigurarCai = "Configuración de CAI";
            public const string BotonUnidadesMedida = "Unidades de medida";
            public const string CampoNombreComercial = "Nombre comercial";
            public const string CampoRtnOpcional = "RTN (14 dígitos, opcional)";
            public const string CampoDireccion = "Dirección";
            public const string CampoTelefono = "Teléfono";
            public const string CampoCorreoContacto = "Correo de contacto";
            public const string CampoLogoNegocio = "Logo del negocio";
            public const string BotonCambiarLogo = "Cambiar logo";
            public const string BotonGuardarCambios = "Guardar cambios";
            public const string SeccionUsuarios = "Usuarios";
            public const string BotonNuevoUsuario = "Nuevo usuario";
            public const string ErrorRtnInvalido = "El RTN debe tener exactamente 14 dígitos numéricos, o dejarse en blanco";
            public const string ErrorNombreComercialRequerido = "El nombre comercial es requerido";
            public const string NoSeCargoConfiguracionPrefijo = "No se pudo cargar la configuración: ";

            public const string RegistroTituloVentana = "Nuevo usuario";
            public const string RegistroTitulo = "Crear nuevo usuario";
            public const string RegistroSubtitulo = "Complete los datos del nuevo usuario.";
            public const string CampoNombreUsuario = "Nombre de usuario";
            public const string CampoNombreCompleto = "Nombre completo";
            public const string CampoPassword = "Contraseña";
            public const string CampoConfirmarPassword = "Confirmar contraseña";
            public const string CampoRol = "Rol";
            public const string BotonGuardar = "Guardar";
            public const string ErrorNombreUsuarioCorto = "El nombre de usuario debe tener al menos 3 caracteres";
            public const string ErrorNombreCompletoRequerido = "El nombre completo es requerido";
            public const string ErrorPasswordCorta = "La contraseña debe tener al menos 6 caracteres";
            public const string ErrorPasswordsNoCoinciden = "Las contraseñas no coinciden";
            public const string ErrorSeleccioneRol = "Seleccione un rol";
        }

        public static class Arranque
        {
            public const string TituloVentana = "Elements System";
            public const string AtribucionCreador = "Creado Por Elements";

            public const string ActivacionTitulo = "Activar licencia";
            public const string ActivacionInstrucciones = "Esta máquina necesita una clave de activación. Envíe el siguiente código al proveedor y pegue aquí la clave que le entreguen.";
            public const string ActivacionCodigoMaquina = "Código de esta máquina:";
            public const string BotonCopiar = "Copiar";
            public const string ActivacionClaveTitulo = "Clave de activación:";
            public const string BotonActivar = "Activar";
            public const string CodigoCopiado = "Código copiado al portapapeles.";

            public const string PrimerUsuarioTitulo = "Crear administrador";
            public const string PrimerUsuarioSubtitulo = "Cree el usuario administrador con el que iniciará sesión.";
            public const string ErrorNoSeDeterminoRolAdmin = "No se pudo determinar el rol de administrador";

            public const string DatosNegocioTitulo = "Datos de su negocio";
            public const string DatosNegocioSubtitulo = "Estos datos identifican su negocio dentro del sistema. El RTN y los demás datos fiscales son opcionales.";
            public const string CampoDireccionOpcional = "Dirección (opcional)";
            public const string CampoTelefonoOpcional = "Teléfono (opcional)";
            public const string CampoCorreoOpcional = "Correo de contacto (opcional)";
            public const string CampoLogoOpcional = "Logo del negocio (opcional)";
            public const string BotonSeleccionarImagen = "Seleccionar imagen";
            public const string BotonContinuar = "Continuar";

            public const string LoginSubtitulo = "Inicie sesión para continuar";
            public const string CampoUsuario = "Usuario";
            public const string BotonEntrar = "Entrar";
            public const string ErrorIngreseUsuarioPassword = "Ingrese usuario y contraseña";
            public const string LoginTituloGenerico = "Iniciar sesión";

            public const string ErrorConexionTitulo = "Error de conexión";
            public const string ErrorConexionMensaje =
                "No se pudo conectar con la base de datos. Verifique que el servidor SQL esté disponible " +
                "y que la base de datos ya haya sido publicada.\n\nDetalle: ";
        }

        // Facturación legal (CAI): vive en Core porque el requisito de
        // facturar con CAI es una obligación fiscal hondureña, no algo
        // propio de una vertical en particular.
        public static class Facturacion
        {
            public const string TituloCaiActivo = "CAI activo";
            public const string TituloRegistrarNuevoCai = "Registrar nuevo rango CAI";
            public const string CampoRangoAutorizado = "Rango autorizado (código SAR)";
            public const string CampoRangoInicial = "Rango inicial (16 dígitos)";
            public const string CampoRangoFinal = "Rango final (16 dígitos)";
            public const string CampoFechaAutorizacion = "Fecha de autorización";
            public const string CampoFechaVencimiento = "Fecha de vencimiento";
            public const string BotonRegistrarCai = "Registrar CAI";
            public const string ErrorCamposRangoIncompletos = "Complete el rango autorizado y los 16 dígitos de rango inicial/final";
            public const string SinCaiConfigurado = "No hay ningún CAI configurado. El punto de venta no podrá registrar ventas hasta que se registre uno abajo.";
            public const string RestantesSinDato = "—";
            public const string EstadoFormato =
                "Rango: {0}\n" +
                "Del {1} al {2}\n" +
                "Correlativo actual: {3}   ·   Restantes: {4}\n" +
                "Vigente del {5:dd/MM/yyyy} al {6:dd/MM/yyyy}";
        }

        // Catálogo de unidades de medida (libras, kilos, metros, varas
        // cuadradas, etc.). Vive en Core porque, igual que Productos, es un
        // concepto genérico que cualquier vertical futura reutiliza.
        public static class UnidadesMedida
        {
            public const string TituloVentana = "Unidades de medida";
            public const string CampoCodigo = "Código";
            public const string CampoNombre = "Nombre";
            public const string CampoSimbolo = "Símbolo";
            public const string CampoPermiteFraccion = "Admite decimales";
            public const string CampoSistema = "Sistema";
            public const string CampoActivo = "Activo";
            public const string BotonAgregar = "Agregar";
            public const string ErrorCamposRequeridos = "Código, nombre y símbolo son requeridos";
            public const string NoSeCargaronPrefijo = "No se pudieron cargar las unidades de medida: ";
            public const string NoSeGuardoPrefijo = "No se pudo guardar: ";
        }
    }
}
