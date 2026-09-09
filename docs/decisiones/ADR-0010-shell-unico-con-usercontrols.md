# ADR-0010 — Ventana única con `UserControl`, sin MDI

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El usuario opera el sistema seis a nueve horas diarias. Necesita saber siempre
dónde está y llegar a cualquier módulo sin buscar. Un enjambre de ventanas
superpuestas —el patrón clásico de los sistemas de escritorio de los noventa—
produce exactamente lo contrario: ventanas perdidas detrás de otras, dudas
sobre cuál está activa, y clics de más en cada tarea.

La [`GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`](../../GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md)
lo plantea como ley: la aplicación entera es **una sola ventana** con regiones
fijas.

## Decisión

`FormDashboardBase` es el **cascarón único**, maximizado, con dos regiones fijas:

- **Sidebar colapsable** a la izquierda (220 px expandido, 56 px colapsado) con
  un ítem por `IDashboardModule` registrado.
- **Panel de contenido** que intercambia el `UserControl` del módulo activo.

Se usa `Panel` + `UserControl`, **no MDI**. Los `Form` quedan reservados para
diálogos modales de captura puntual (`FormRegistrarCompra`, `FormProveedor`,
`FormRegistrarPago`), no para navegar.

Todas las ventanas heredan de `FormBase`, que fija posición, fuente y fondo, y
aporta `MostrarError`, `MostrarInfo` y `Confirmar`.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| MDI clásico | En WinForms moderno complica el estilo y el ciclo de vida de los controles sin aportar nada acá. Y produce el enjambre de ventanas que se quiere evitar |
| Una ventana por módulo | Igual de desorientador, y multiplica el manejo de estado y de foco |
| Pestañas | Mejor que MDI, pero el usuario termina con quince pestañas abiertas y el mismo problema de "dónde estoy" |

## Consecuencias

**A favor**
- El usuario aprende la anatomía de la pantalla una vez y le sirve para los 40
  módulos.
- El ciclo de vida es simple: se monta un control, se desmonta el anterior.
- El sidebar colapsable gana ancho en pantallas chicas sin perder la navegación.

**En contra**
- No se pueden ver dos módulos a la vez. Es una concesión deliberada: la
  alternativa cuesta más de lo que devuelve para este usuario.
- Cada módulo debe limpiar lo suyo al desmontarse; nada del compilador lo obliga.
