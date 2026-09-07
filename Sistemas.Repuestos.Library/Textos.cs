namespace Sistemas.Repuestos.Library
{
    // Único lugar donde viven los textos propios de la vertical de
    // Repuestos (inventario, POS, ventas, compras, proveedores, cuentas).
    // Los textos compartidos por cualquier vertical viven en
    // Sistemas.Core.UI/Textos.cs; los de la capa de negocio compartida, en
    // Sistemas.Core/Textos.cs. La facturación legal (CAI) también vive en
    // Sistemas.Core.UI/Textos.cs — es una obligación fiscal hondureña, no
    // algo propio de esta vertical. Los encabezados de columna de los
    // DataGridView (HeaderText) se dejan inline junto a su definición: ya
    // están colocados junto al DataPropertyName que describen, así que
    // extraerlos no facilita nada.
    public static class Textos
    {
        public static class Modulos
        {
            public const string Inventario = "Inventario";
            public const string Proveedores = "Proveedores";
            public const string Clientes = "Clientes";
            public const string Compras = "Compras";
            public const string Pos = "POS";
            public const string Caja = "Caja";
            public const string Ventas = "Ventas";
        }

        // Textos reutilizados por varias pantallas de esta vertical.
        public static class Comun
        {
            public const string BotonNuevo = "Nuevo";
            public const string BotonEditar = "Editar";
            public const string BotonBuscar = "Buscar";
            public const string BotonGuardar = "Guardar";
            public const string BotonAgregar = "Agregar";
            public const string CampoBuscar = "Buscar";
            public const string CampoCantidad = "Cantidad";
            public const string CampoActivo = "Activo";
            public const string CampoSoloActivos = "Solo activos";
            public const string CampoProveedor = "Proveedor";
            public const string ErrorBusqueSeleccioneProductoPrimero = "Busque y seleccione un producto primero";
            public const string NoSeConectoBdPrefijo = "No se pudo conectar con la base de datos: ";
            public const string NoSePudoGuardarPrefijo = "No se pudo guardar: ";
            public const string NoSePudoBuscarPrefijo = "No se pudo buscar: ";
            public const string NoSePudoAgregarPrefijo = "No se pudo agregar: ";
            public const string FiltroExcel = "Excel (*.xlsx)|*.xlsx";
        }

        public static class Inventario
        {
            public const string CategoriaTodas = "(Todas)";
            public const string BotonImportarExcel = "Importar Excel";
            public const string BotonExportarExcel = "Exportar Excel";
            public const string BotonDescargarPlantilla = "Descargar plantilla";
            public const string BotonArmarPaquete = "Armar paquete";
            public const string CampoCategoria = "Categoría";
            public const string TituloEditar = "Editar";
            public const string ErrorSeleccioneProductoPrimero = "Seleccione un producto primero.";
            public const string ErrorSeleccionePaqueteProducto = "Seleccione el producto que va a ser el paquete.";
            public const string TituloArmarPaquete = "Armar paquete";
            public const string TituloExportar = "Exportar";
            public const string FormatoExportoOk = "Se exportaron {0} producto(s) a {1}";
            public const string NoSePudoExportarPrefijo = "No se pudo exportar: ";
            public const string TituloPlantilla = "Plantilla";
            public const string PlantillaGeneradaEnPrefijo = "Plantilla generada en ";
            public const string NoSeGeneroPlantillaPrefijo = "No se pudo generar la plantilla: ";
            public const string NoSeCargaronCategoriasPrefijo = "No se pudieron cargar las categorías: ";

            public const string CategoriaRapidaTituloVentana = "Nueva categoría";
            public const string CampoNombreCategoria = "Nombre de la categoría";
            public const string BotonCrear = "Crear";
            public const string ErrorNombreRequerido = "El nombre es requerido";
            public const string NoSeCreoCategoriaPrefijo = "No se pudo crear la categoría: ";

            public const string ImportarTituloVentana = "Importar productos desde Excel";
            public const string ImportarInstruccionesPrefijo = "Seleccione un archivo .xlsx con las columnas exactas: ";
            public const string BotonSeleccionarArchivo = "Seleccionar archivo...";
            public const string BotonImportar = "Importar";
            public const string EstadoImportando = "Importando...";
            public const string NoSePudoImportarPrefijo = "No se pudo importar: ";

            public const string ArmarPaqueteTituloFormato = "Armar paquete — {0} · {1}";
            public const string ArmarPaqueteAviso = "Busque los productos que forman este paquete y agréguelos con su cantidad.";
            public const string CampoBuscarComponente = "Buscar componente";
            public const string BotonQuitarSeleccionado = "Quitar seleccionado";
            public const string BotonGuardarPaquete = "Guardar paquete";
            public const string ErrorAgregueUnComponente = "Agregue al menos un componente";
            public const string NoSeArmoPaquetePrefijo = "No se pudo armar el paquete: ";

            public const string ProductoTituloNuevo = "Nuevo producto";
            public const string ProductoTituloEditarFormato = "Editar producto — {0}";
            public const string TabGeneral = "General";
            public const string TabRepuesto = "Repuesto";
            public const string TabVehiculos = "Vehículos compatibles";
            public const string TabEquivalencias = "Equivalencias OEM";
            public const string TabPrecios = "Proveedores y precios";
            public const string CampoCodigo = "Código";
            public const string CampoCodigoBarra = "Código de barras (opcional)";
            public const string CampoNombre = "Nombre";
            public const string CampoDescripcion = "Descripción";
            public const string CampoPrecioUnitario = "Precio unitario (L.)";
            public const string CampoTasaIsv = "Tasa ISV";
            public const string CampoStockMinimo = "Stock mínimo";
            public const string ErrorCodigoRequerido = "El código es requerido";
            public const string BotonCrearProducto = "Crear producto";
            public const string BotonGuardarCambios = "Guardar cambios";
            public const string CampoNumeroParte = "Número de parte";
            public const string CampoMarcaFabricante = "Marca fabricante";
            public const string CampoEsOriginal = "Es original (no genérico)";
            public const string CampoMarca = "Marca";
            public const string CampoModelo = "Modelo";
            public const string CampoAnioDesde = "Año desde";
            public const string CampoAnioHasta = "Año hasta";
            public const string ErrorMarcaModeloRequeridos = "Marca y modelo son requeridos";
            public const string CampoNumeroOem = "Número OEM";
            public const string CampoFabricante = "Fabricante";
            public const string ErrorNumeroOemRequerido = "El número OEM es requerido";
            public const string CampoPrecioCompra = "Precio de compra (L.)";
            public const string ErrorSeleccioneProveedor = "Seleccione un proveedor";
            public const string BotonCerrar = "Cerrar";
            public const string NoSeCargoDetalleRepuestoPrefijo = "No se pudo cargar el detalle de repuesto: ";
            public const string NoSeGuardoPrecioPrefijo = "No se pudo guardar el precio: ";
        }

        // Campos y mensajes compartidos entre las vistas "Proveedores" y
        // "Clientes" — ambas son la misma entidad Tercero, así que un mismo
        // registro de textos alimenta TerceroCamposControl/FormTercero/
        // FormPerfilTercero/TercerosControl en las dos vistas. Los pocos
        // textos que sí varían por vista (título, mensajes de error que
        // nombran el rol) quedan como formato parametrizado por
        // RolProveedor/RolCliente en vez de duplicarse por completo.
        public static class Terceros
        {
            public const string CampoNombre = "Nombre";
            public const string CampoEmpresa = "Empresa (opcional)";
            public const string CampoCorreo = "Correo (opcional)";
            public const string CampoTelefono = "Teléfono (opcional)";
            public const string CampoRtnOpcional = "RTN (14 dígitos, opcional)";
            public const string CampoEsProveedor = "Es proveedor";
            public const string CampoEsCliente = "Es cliente";
            public const string ErrorNombreRequerido = "El nombre es requerido";
            public const string ErrorRtnInvalido = "El RTN debe tener exactamente 14 dígitos, o dejarse en blanco";
            public const string ErrorCorreoInvalido = "El correo no tiene un formato válido, o déjelo en blanco";
            public const string ErrorAlMenosUnRol = "Debe marcar al menos un rol (proveedor o cliente)";

            // Nombre del rol en minúscula/mayúscula, usado para construir los
            // textos que varían por vista (Proveedores vs. Clientes) sin
            // duplicar cada mensaje.
            public const string RolProveedorMinuscula = "proveedor";
            public const string RolClienteMinuscula = "cliente";
            public const string RolProveedorCapitalizado = "Proveedor";
            public const string RolClienteCapitalizado = "Cliente";

            public const string FormularioTituloNuevoFormato = "Nuevo {0}";
            public const string FormularioTituloEditarFormato = "Editar {0}";
            public const string PerfilTituloFormato = "Perfil de {0} — {1}";
            public const string ErrorSeleccionePrimeroFormato = "Seleccione un {0} primero.";
        }

        public static class Compras
        {
            public const string RegistrarTituloVentana = "Registrar compra";
            public const string CampoProveedor = "Proveedor";
            public const string CampoNumeroFacturaProveedor = "N° factura del proveedor";
            public const string CampoCompraCredito = "Compra a crédito";
            public const string CampoDiasCredito = "Días crédito";
            public const string CampoBuscarProducto = "Buscar producto";
            public const string CampoCostoUnitario = "Costo unitario (L.)";
            public const string BotonQuitarLinea = "Quitar línea";
            public const string FormatoTotal = "Total: L. {0:N2}";
            public const string ErrorSeleccioneProveedor = "Seleccione un proveedor";
            public const string ErrorAgregueUnaLinea = "Agregue al menos una línea";
            public const string NoSeRegistroCompraPrefijo = "No se pudo registrar la compra: ";
            public const string NoSeCargaronProveedoresPrefijo = "No se pudieron cargar los proveedores: ";
            public const string BotonNuevaCompra = "Nueva compra";
            public const string BotonActualizar = "Actualizar";
        }

        // Pantalla de facturación rápida (carrito + cobro + impresión). Es
        // lo que antes se llamaba "Ventas" — el nombre "Ventas" ahora es el
        // historial (ver Textos.Ventas más abajo).
        public static class Pos
        {
            public const string CampoBuscarProducto = "Buscar producto";
            public const string CampoBuscarPorEquivalencia = "Buscar por número equivalente (OEM)";
            public const string CampoCantidadCorta = "Cant.";
            public const string BotonAgregarAlCarrito = "Agregar al carrito";
            public const string BotonQuitarLinea = "Quitar línea";
            public const string CampoVentaCredito = "Venta a crédito";
            public const string CampoDiasCredito = "Días crédito";
            public const string CampoCliente = "Cliente";
            public const string ErrorSeleccioneClienteCredito = "Seleccione un cliente para venta a crédito";
            public const string NoSeCargaronClientesPrefijo = "No se pudieron cargar los clientes: ";
            public const string FormatoTotal = "Total: L. {0:N2}";
            public const string BotonCobrar = "Cobrar";
            public const string ErrorCarritoVacio = "El carrito está vacío";
            public const string NoSeRegistroVentaPrefijo = "No se pudo registrar la venta: ";
            public const string BotonImprimir = "Imprimir";
            public const string BotonNuevaVenta = "Nueva venta";
            public const string ResumenFacturaFormato = "Venta registrada\n\nFactura: {0}\nFecha: {1:dd/MM/yyyy HH:mm}\nTotal: L. {2:N2}";
            public const string FacturaVentaGenerico = "Factura de venta";

            public const string ReciboEncabezadoFormato = "{0} — Factura de venta";
            public const string ReciboFacturaFormato = "Factura: {0}";
            public const string ReciboFechaFormato = "Fecha: {0:dd/MM/yyyy HH:mm}";
            public const string ReciboColumnaProducto = "Producto";
            public const string ReciboColumnaCantidad = "Cant";
            public const string ReciboColumnaPrecioUnitario = "P.Unit";
            public const string ReciboColumnaSubtotal = "Subtotal";
            public const string ReciboTotalFormato = "TOTAL: L. {0:N2}";
            public const string ReciboEfectivoRecibidoFormato = "Efectivo recibido: L. {0:N2}";
            public const string ReciboVueltoFormato = "Vuelto: L. {0:N2}";

            public const string CampoMetodoPago = "Método de pago";
            public const string MetodoPagoEfectivo = "Efectivo";
            public const string MetodoPagoTarjeta = "Tarjeta";
            public const string MetodoPagoTransferencia = "Transferencia";

            public const string AvisoCajaCerrada = "No hay una sesión de caja abierta. Abra la caja para poder cobrar.";
            public const string BotonAbrirCajaDesdePos = "Abrir caja";
            public const string NoSeVerificoCajaPrefijo = "No se pudo verificar el estado de la caja: ";

            public const string CobroEfectivoTitulo = "Cobro en efectivo";
            public const string CobroEfectivoTotalFormato = "Total a cobrar: L. {0:N2}";
            public const string CobroEfectivoCampoRecibido = "Efectivo recibido (L.)";
            public const string CobroEfectivoBotonLimpiar = "Limpiar";
            public const string CobroEfectivoVueltoFormato = "Vuelto: L. {0:N2}";
            public const string CobroEfectivoBotonConfirmar = "Confirmar cobro";
        }

        // Historial de ventas (antes era el diálogo FormHistorialVentas,
        // ahora es el contenido del módulo "Ventas" de la barra lateral).
        public static class Ventas
        {
            public const string Titulo = "Historial de ventas";
            public const string CampoNumeroFactura = "N° de factura";
            public const string CampoSoloVigentes = "Solo vigentes (no anuladas)";
            public const string CampoMotivoAnulacion = "Motivo de anulación (requerido para anular)";
            public const string BotonAnularVenta = "Anular venta seleccionada";
            public const string ErrorSeleccioneVentaPrimero = "Seleccione una venta primero";
            public const string ErrorVentaYaAnulada = "Esta venta ya está anulada";
            public const string ErrorIndiqueMotivoAnulacion = "Indique el motivo de la anulación";
            public const string ConfirmarAnularFormato = "¿Anular la factura {0} por L. {1:N2}? Esta acción restaura el stock vendido.";
            public const string NoSeAnuloPrefijo = "No se pudo anular: ";
        }

        public static class Cuentas
        {
            public const string CampoSoloConSaldo = "Solo con saldo pendiente";
            public const string BotonRegistrarPago = "Registrar pago";
            public const string TituloRegistrarPago = "Registrar pago";
            public const string ErrorSeleccioneCuentaPrimero = "Seleccione una cuenta primero.";
            public const string ErrorCuentaSinSaldo = "Esta cuenta ya no tiene saldo pendiente.";

            public const string PagoFormularioTitulo = "Registrar pago";
            public const string PagoSaldoPendienteFormato = "Saldo pendiente: L. {0:N2}";
            public const string CampoMontoAPagar = "Monto a pagar (L.)";
            public const string CampoMetodoPago = "Método de pago";
            public const string BotonRegistrarPagoAccion = "Registrar pago";
            public const string NoSeRegistroPagoPrefijo = "No se pudo registrar el pago: ";
        }

        // Sesiones de caja: apertura, cierre e historial. Mismo estilo que
        // Textos.Cuentas.
        public static class Caja
        {
            public const string AbrirTitulo = "Abrir caja";
            public const string CampoMontoApertura = "Monto inicial de caja (L.)";
            public const string BotonAbrirCaja = "Abrir caja";
            public const string NoSeAbrioCajaPrefijo = "No se pudo abrir la caja: ";

            public const string CerrarTitulo = "Cerrar caja";
            public const string CalculandoMontoEsperado = "Calculando monto esperado...";
            public const string FormatoMontoEsperado = "Monto esperado: L. {0:N2}";
            public const string NoSeCargoMontoEsperadoPrefijo = "No se pudo calcular el monto esperado: ";
            public const string CampoEfectivoContado = "Efectivo contado (L.)";
            public const string BotonCerrarCaja = "Cerrar caja";
            public const string NoSeCerroCajaPrefijo = "No se pudo cerrar la caja: ";
            public const string FormatoResultadoCierre = "{0}\n\nMonto calculado: L. {1:N2}\nDiferencia: L. {2:N2}";

            public const string EstadoCerrada = "No hay una sesión de caja abierta.";
            public const string EstadoAbiertaFormato = "Caja abierta por {0} desde {1:dd/MM/yyyy HH:mm} — Monto inicial: L. {2:N2}";
            public const string UsuarioGenericoFormato = "Usuario #{0}";
        }
    }
}
