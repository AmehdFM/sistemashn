# ADR-0004 — Aplicación de escritorio WinForms, no web

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El cliente objetivo no tiene internet confiable, tiene cortes de energía y usa
PCs viejas con Windows. El usuario factura con el teclado durante ocho horas
seguidas. Y hay que imprimir en una impresora térmica de recibos conectada
localmente.

## Decisión

Aplicación de **escritorio Windows con WinForms** sobre .NET 10, apuntando a
`net10.0-windows`.

Las pantallas se construyen **por código, no con el diseñador**: el diseñador
genera `.Designer.cs` con colores y textos literales incrustados, que rompe la
centralización de [ADR-0007](ADR-0007-textos-centralizados-por-capa.md). No hay
ningún `.Designer.cs` en el repositorio y no debería aparecer.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Aplicación web (Blazor, ASP.NET) | Exige un servidor corriendo en el local, un navegador encima y un modelo mental más complejo para respaldar y actualizar. El acceso al hardware local (impresora térmica, lector de códigos, WMI para el fingerprint de licencia) se vuelve un problema |
| WPF | Más capaz visualmente, pero el rendimiento gráfico en hardware viejo con drivers pobres es peor, y para pantallas densas de grilla y formulario WinForms alcanza de sobra |
| MAUI / multiplataforma | El cliente es Windows. Pagar la abstracción multiplataforma sin usarla es costo puro |
| Electron o similar | Consumo de memoria inaceptable en la máquina objetivo |

## Consecuencias

**A favor**
- Un `.exe` que se copia y funciona; sin servidor, sin navegador, sin puertos.
- Acceso directo a impresora, WMI y sistema de archivos.
- Control total del teclado, que es el requisito de usabilidad número uno.
- Rendimiento predecible en hardware viejo.

**En contra**
- Solo Windows, para siempre.
- Sin diseñador visual: cada pantalla es código, y por eso la
  [`GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`](../../GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md)
  y los helpers compartidos (`FormBase`, `GridStyler`, `PaginacionControl`,
  `UiTheme`) son indispensables, no opcionales.
- Actualizar exige llegar a cada máquina ([ADR-0014](ADR-0014-despliegue-por-dacpac.md)).
