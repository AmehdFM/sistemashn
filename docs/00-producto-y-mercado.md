# 00 — Producto y mercado

## 1. El problema que resuelve

La PyME hondureña lleva su inventario y sus ventas en cuadernos, en Excel o en
un sistema pirateado de hace quince años que nadie sabe respaldar. Cuando llega
el momento de facturar con CAI ante el SAR, la papelería se lleva a mano y el
correlativo se controla en una libreta. El resultado predecible: se vende
producto que no hay, se pierde el rastro del crédito que se dio, y una falla del
disco duro borra el negocio entero.

Las alternativas que existen fallan por el mismo lado: **asumen internet**.
Un SaaS de facturación no sirve en un local donde la conexión se cae tres veces
al día y la luz se va sin aviso.

## 2. A quién se le vende

**Cliente típico:** PyME hondureña con **1 a 3 terminales**.

- Dueño que atiende, más uno o dos empleados.
- Una PC de escritorio de varios años, Windows, disco mecánico, poca RAM.
- Red local sencilla o, muchas veces, una sola máquina que es todo.
- Sin personal de sistemas. Cuando algo falla, llaman por teléfono.
- Facturan con CAI del SAR, ISV del 15 %, en lempiras.

**Usuario del software:** empleado no técnico, sin entrenamiento previo, que va
a usar la aplicación 6–9 horas diarias todos los días durante años. La métrica
de éxito no es que le guste: es **segundos por transacción y errores por turno**.

## 3. Qué se vende exactamente

Un sistema de escritorio que se instala en la máquina del cliente y le
pertenece. Concretamente:

- **Núcleo (Core):** usuarios y roles, catálogo de productos con unidades de
  medida y categorías, facturación CAI, configuración del negocio con marca
  propia, auditoría de operaciones.
- **Vertical por rubro:** los módulos específicos del giro. Hoy
  **autorepuestos** (proveedores, compras, paquetes/kits, POS, ventas,
  cuentas por cobrar y por pagar). La próxima prevista es **ferretería y
  materiales de construcción**.
- **Herramientas de operación:** respaldo automático, purga de auditoría,
  verificación de integridad de la base.

## 4. Modelo de negocio

**Licencia perpetua por máquina.** El cliente compra una vez y el software es
suyo, sin renta mensual y sin dejar de funcionar si no renueva. Esto es
deliberado: en este mercado, el rechazo a la suscripción es fuerte y la
desconfianza a "que me lo apaguen" es real.

Mecánica de activación, toda offline:

1. El cliente instala y ve un **código de máquina** en la pantalla de
   activación: un SHA-256 de CPU + disco + placa madre.
2. Lo dicta o lo envía por WhatsApp.
3. El vendedor lo pega en `Sistemas.Licencias` (herramienta interna, **nunca se
   distribuye**), que emite una **clave firmada con RSA** atada a ese código.
4. El cliente la escribe una vez. La app verifica la firma con la clave pública
   embebida y la guarda cifrada con DPAPI a nivel de máquina.

Consecuencias que hay que respetar en el código:
- La clave privada (`clave_privada.pem`) es el activo más valioso del negocio y
  está en `.gitignore`. Nunca se sube a ningún repositorio.
- La licencia admite vigencia opcional, lo que deja abierta la puerta a vender
  mantenimiento anual sin cambiar el mecanismo.
- Nada de esto toca la red. Una validación en línea rompería el producto.

## 5. Por qué gana (y dónde no compite)

**Dónde gana:**
- **Funciona sin internet, siempre.** No es una limitación aceptada: es la
  característica.
- **Sobrevive al corte de luz.** Durabilidad estricta en cada transacción y
  respaldo automático como parte del producto.
- **Corre en la PC que el cliente ya tiene.** Paginación en servidor, índices
  que cubren la consulta, sin pantallas que traigan la tabla entera.
- **Habla como el cliente.** Todo en español de Honduras, con CAI, ISV y
  lempiras de primera clase, no como una localización agregada después.
- **Marca blanca.** El cliente ve su propio logo y el nombre de su negocio.

**Dónde no compite (y está bien):**
- Empresas con varias sucursales que necesitan consolidación en tiempo real.
- Contabilidad completa (libros, planilla, activos fijos). El sistema registra
  la operación; no reemplaza al contador.
- Cualquier cosa que exija estar en línea: tienda web, app móvil, portal.

## 6. Consecuencias de diseño no negociables

Todo lo anterior se traduce en el código de esta forma. Si una propuesta técnica
contradice alguna de estas líneas, la propuesta está mal, no la línea.

| Realidad del mercado | Cómo se ve en el código |
|---|---|
| Sin internet | Cero llamadas de red en toda la solución. Licencia offline. `SYSDATETIME()` y no UTC. |
| Cortes de luz | Transacciones atómicas y durables. `DELAYED_DURABILITY` prohibido. Respaldo automático. |
| Hardware viejo | Todo listado paginado en servidor. Índices justificados uno por uno. |
| Express 10 GB | Purga de auditoría por antigüedad desde el día uno. |
| Sin soporte en sitio | Ningún error crudo en pantalla; `Exito`/`Mensaje` en español y detalle a auditoría. |
| Muchas copias instaladas | Versionado de esquema y actualización por DACPAC. |
| Un rubro hoy, otro mañana | Core compartido + verticales enchufables por `IVerticalModuleProvider`. |
| Negocio del cliente, no el nuestro | Marca blanca: logo y datos del negocio configurables. |
