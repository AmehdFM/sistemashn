# Manual de operación — SistemasHN Repuestos

Este manual es para el propietario del negocio y las personas que usan SistemasHN día a día
(cajero, administrador). No sustituye asesoría legal ni tributaria; ver
`docs/investigacion-facturacion-honduras.md` para el alcance real de la facturación fiscal.

## 1. Activación (primer arranque)

SistemasHN funciona sin internet. La activación usa una **licencia offline** atada a la
máquina donde se instala (ver "Reactivación por cambio de hardware" más abajo si cambia de
equipo).

- **En desarrollo/pruebas**: el script `activar_licencia.py` en la raíz del repositorio genera
  y firma una licencia de prueba con una clave de desarrollo, e imprime el código de
  activación (`SHNLIC1...`) para pegarlo en la pantalla de primer arranque.
- **En producción, con un cliente real**: el flujo es el mismo, pero el código de activación lo
  genera y firma el vendedor (con su clave privada real, nunca la de desarrollo) a partir del
  **código de solicitud** que la pantalla de primer arranque del cliente muestra (contiene la
  huella de esa máquina). El vendedor nunca necesita acceso remoto a la PC del cliente para
  activarla: el intercambio de códigos puede ser por teléfono, correo o mensaje.
- Tras pegar el código de activación, la app pide crear el negocio (nombre, RTN, dirección,
  etc.) y el primer usuario administrador.

## 2. Respaldo

El respaldo protege la única copia de los datos del negocio: sin uno reciente y verificado,
una falla de disco o un borrado accidental puede significar perder todo el historial de ventas,
inventario y clientes.

- Pantalla **Respaldos** (menú "Configuración avanzada" en la barra lateral, requiere el
  permiso "Gestionar respaldos"):
  - **Respaldar ahora**: copia la base de datos activa a una carpeta que usted elija (se
    recomienda un disco externo o una carpeta sincronizada a la nube, NUNCA solo la misma PC).
  - El respaldo se verifica automáticamente al crearse (integridad del archivo); si algo sale
    mal, la app avisa y no deja un respaldo corrupto a medias.
  - La pantalla muestra un **recordatorio** si no hay un respaldo verificado en las últimas 24
    horas, o si nunca se ha hecho ninguno.
- **Recomendación de frecuencia**: al menos una vez al día, al cerrar el negocio, y siempre
  antes de una actualización (ver sección 4).
- Guarde respaldos de varios días distintos, no solo el más reciente: si un respaldo resulta
  estar dañado (poco común, ya que se verifica al crearse, pero puede corromperse después por
  el medio donde se guardó), necesita uno anterior de respaldo.

## 3. Restauración (siempre primero en ensayo)

**Nunca restaure directamente sobre la base de datos activa sin haber probado el respaldo
primero.** La pantalla de Respaldos ofrece **Restaurar en ensayo**: crea una copia de prueba en
una carpeta aparte, para verificar que el respaldo elegido abre y se ve correcto, sin tocar en
ningún momento los datos con los que se está trabajando hoy.

Si necesita volver a un respaldo anterior como base activa (por ejemplo, tras corrupción de
datos confirmada), ese es un procedimiento manual fuera de la app (reemplazar el archivo de
base de datos con la PC apagada/la app cerrada): contacte soporte antes de hacerlo si no está
seguro.

## 4. Actualización

- **Actualización normal (por paquete ZIP local firmado)**: en la pantalla de
  Respaldos/Actualizaciones, "Aplicar paquete local (ZIP)": el administrador elige el archivo
  `.zip` que le entregó el vendedor, la app valida su firma y su contenido, muestra un resumen
  (versión origen → destino) y pide confirmación. Al confirmar, la app se cierra y un proceso
  separado (`updater`) reemplaza los archivos del programa y migra la base de datos si hace
  falta.
  - **Haga un respaldo antes de actualizar.** Si la actualización falla a mitad de camino, el
    sistema revierte automáticamente el programa y la base de datos a como estaban antes de
    empezar — pero un respaldo aparte es la red de seguridad final.
  - Si la actualización falla y revierte, la app vuelve a abrir en la versión anterior sin
    pérdida de datos; el mensaje de error indica qué pasó. Contacte soporte con ese mensaje.
- **"Buscar actualización por internet"** aparece deshabilitado: esta versión no incluye un
  servidor de actualizaciones remoto (ver "Fuera de alcance" en
  `docs/superpowers/plans/fase-6-operacion-entrega.md`, sección T6.5). Las actualizaciones
  llegan como archivo ZIP entregado por el vendedor.

## 5. Soporte y recuperación de administrador

Si todos los administradores olvidan su contraseña y no hay códigos de recuperación guardados:

1. En la pantalla de inicio de sesión, la opción de recuperación genera un **desafío** (texto
   con un identificador de esa instalación y un código de un solo uso).
2. Envíe ese texto al vendedor/soporte técnico.
3. El vendedor firma una autorización de recuperación con su clave privada (nunca necesita
   acceso remoto a la PC) y se la devuelve como un token de texto.
4. Se pega ese token en la app para restablecer la contraseña del administrador principal. El
   token es de un solo uso y expira en menos de 72 horas.

Alternativa más rápida si se generaron **códigos de recuperación** al crear el negocio (formato
`XXXX-XXXX-XXXX`): cualquiera de esos códigos, guardado en un lugar seguro fuera de la PC,
permite restablecer el acceso sin depender del vendedor. Regenerarlos invalida los anteriores;
anótelos de nuevo si los regenera.

## 6. Reactivación por cambio de hardware

La licencia está atada a la huella de la máquina (identificador de Windows + número de serie
del disco del sistema). Si el negocio cambia de PC (equipo nuevo, reemplazo de disco del
sistema, reinstalación de Windows que cambie esos identificadores), la app pedirá activarse de
nuevo:

1. La nueva PC muestra su propio código de solicitud en la pantalla de primer arranque.
2. Contacte al vendedor con ese código (mismo procedimiento que la activación inicial).
3. El vendedor emite un nuevo código de activación para la máquina nueva.

Este es un procedimiento manual con el vendedor; no hay reactivación automática por internet en
esta versión.

## 7. Límites conocidos de esta versión

- **Una PC por instalación**: los datos viven en una base de datos local (SQLite) en esa
  máquina; no hay modo de red con varias cajas compartiendo el mismo inventario en tiempo real.
  Para varias cajas, cada una necesita su propia instalación y los datos no se sincronizan entre
  ellas automáticamente.
- **Factura fiscal**: la emisión de factura fiscal (CAI) existe en el sistema pero está
  **apagada por defecto**. Activarla requiere que el negocio tenga su propia autorización de
  autoimpresor ante el SAR; el sistema no la tramita ni la reemplaza. Mientras tanto, el
  "comprobante genérico" que emite el sistema es un documento interno, no una factura fiscal.
- **Impresión**: usa la impresora predeterminada de Windows; no se ha probado con una impresora
  física en este ciclo de desarrollo (queda pendiente de verificar por el propietario con su
  hardware real).
- **Actualización obligatoria remota**: no existe en esta versión (ver sección 4); toda
  actualización se entrega y aplica manualmente por el vendedor.
