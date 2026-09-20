# 05 — Estado real y roadmap

> **Última revisión del estado:** 2026-09-20, contra el árbol de trabajo
> vigente, incluido el programa de mejora UI/UX aún sin commit.
>
> Este documento dice qué existe **de verdad**. Si una IA lee "hecho" donde hay
> un stub, va a construir sobre aire. Actualizalo al cerrar cada fase.

---

## 1. Estado por proyecto

| Proyecto | Estado | Detalle |
|---|---|---|
| `Sistemas.Core` | 🟢 Funcional | Seguridad, inventario, categorías, unidades, etiquetas, configuración, facturación CAI, licencias, exportación Excel, archivos |
| `Sistemas.Core.UI` | 🟢 Funcional | Arranque de 4 pasos, dashboard con sidebar, ajustes, CAI, unidades de medida, tema, paginación, estilo de grilla |
| `Sistemas.Core.Database` | 🟢 Funcional | 5 esquemas con tablas, SPs, función de ISV, TVP y post-despliegue idempotente |
| `Sistemas.Repuestos.Database` | 🟢 Implementado | Fases 0–6 del plan: catálogo extendido, proveedores, compras, paquetes, ventas, cuentas |
| `Sistemas.Repuestos.Library` | 🟢 Funcional | Inventario maestro-detalle, proveedores, compras, POS, ventas, cuentas, importación Excel |
| `Sistemas.Repuestos` | 🟢 Funcional | Ejecutable de la vertical |
| `Sistemas.Licencias` | 🟢 Funcional | Generador de claves firmadas por consola |
| `Sistemas.Mantenimiento` | 🔴 **Stub** | `Program.cs` imprime "Hello, World!". `BackupService` y `ClearService` son clases vacías |
| `Sistemas.Core/Logging` | 🔴 **Stub** | Serilog está referenciado pero `LoggerConfig.cs` es una clase vacía. **No hay logging a archivo funcionando** |

## 2. Lo que hay que saber antes de tocar algo

- **No hay proyecto de pruebas** en la solución. Ver
  [`07-estrategia-de-pruebas.md`](07-estrategia-de-pruebas.md).
- **No hay CI.** No hay `.github/workflows` ni equivalente.
- **No hay instalador.** El despliegue objetivo está descrito pero no
  implementado. Ver [`06-despliegue-y-operacion.md`](06-despliegue-y-operacion.md).
- **No hay ningún cliente en producción.** Todavía se puede cambiar cualquier
  cosa que rompa datos existentes, y esa ventana se cierra con la primera
  instalación real.
- **Los `.sqlproj` solo compilan en Windows** con Visual Studio o los SDK de
  SSDT. En Linux se editan los `.sql`, no se produce el DACPAC.

## 3. Bloqueadores para la primera instalación real

En orden. Ninguno es opcional.

### 🔴 B1 — `Sistemas.Mantenimiento` está vacío
Es lo único de esta lista cuya ausencia puede costar el negocio entero de un
cliente. Sin esto, un disco que falla borra la contabilidad del cliente y no hay
vuelta atrás. Falta:
- Respaldo automático programado, con `HistorialRespaldos` registrando resultado
- Purga de auditoría por antigüedad (`sp_PurgarAuditoria`)
- `DBCC CHECKDB` periódico
- Restauración probada — **un respaldo que nunca se restauró no es un respaldo**

### 🔴 B2 — Decidir la collation antes de cargar datos
[ADR-0016](decisiones/ADR-0016-collation-acento-insensitiva.md). Cambiarla con
datos ya cargados es una migración completa, no un `ALTER`. Hoy es
acento-sensitiva: `bujia` no encuentra `bujía`.

### 🔴 B3 — Logging real
Serilog está referenciado y sin configurar. Cuando un cliente llame por teléfono
diciendo "no me deja facturar", hoy no hay nada que leer.

### 🟡 B4 — Empaquetado y actualización
Sin un procedimiento repetible, actualizar 30 instalaciones offline es inviable.

### 🟡 B5 — Resolver las decisiones abiertas
ADR-0016 a ADR-0021. Al menos ADR-0016 (collation), ADR-0018 (paquetes
históricos) y ADR-0019 (anulación a crédito con pagos) antes de vender.

## 4. Roadmap

### Fase A — Dejar el producto instalable *(actual)*
1. `Sistemas.Mantenimiento` completo: respaldo, purga, `CHECKDB`, restauración probada
2. Logging con Serilog configurado y con rotación de archivos
3. Resolver ADR-0016, ADR-0018, ADR-0019, ADR-0021
4. Recorrido manual completo de la checklist de `07-estrategia-de-pruebas.md`
5. Procedimiento de instalación escrito y ejecutado en una máquina limpia

### Estado del programa UI/UX

- La migración estática de shell, listas, diálogos, arranque, ajustes,
  inventario, POS, compras e importaciones está registrada como **Migrada**
  en `docs/ui-ux/04-matriz-migracion-pantallas.md`.
- Ninguna pantalla se declara **Conforme** todavía: faltan recorridos manuales
  con datos reales, teclado, estados de error, 1366×768 y 1920×1080 a
  100/125/150 % de DPI.
- `scripts/validar-ui.ps1`, `git diff --check` y la compilación de
  `Sistemas.Repuestos` son las verificaciones estáticas obligatorias mientras
  no exista evidencia visual.

### Fase B — Primer cliente
1. Instalación asistida en el local del cliente
2. Carga del catálogo real por importación de Excel
3. Medir la búsqueda de productos con datos reales → resolver
   [ADR-0017](decisiones/ADR-0017-estrategia-de-busqueda-de-productos.md) con
   datos, no con suposiciones
4. Acompañamiento en las primeras semanas y registro de fricciones reales

### Fase C — Segunda vertical: ferretería / materiales
La más cercana a autorepuestos: catálogo grande, unidades de medida diversas,
venta de mostrador. Es la prueba de fuego de la arquitectura: **si construirla
obliga a tocar Core, la abstracción falló** y hay que arreglarla ahí, no
parchear la vertical.

Diferencias previsibles a resolver:
- Venta por peso y por longitud (metro, quintal, libra) — ya soportado en parte
  por `UnidadesMedida.PermiteFraccion`
- Conversión entre unidades (comprar por quintal, vender por libra)
- Sin equivalencias OEM ni compatibilidad vehicular: esas tablas son propias de
  autorepuestos y **no deben subir a Core**

### Fase D — Consolidación
- Reportes e impresión más allá del recibo
- Multi-terminal en red local probado en serio
- Lo que el primer cliente pida y se repita en el segundo

## 5. Fuera de alcance, y por qué

Decirlo explícitamente evita que alguien lo empiece:

| No se hace | Por qué |
|---|---|
| Versión web o móvil | El producto es "funciona sin internet". Sería otro producto |
| Sincronización entre sucursales | El cliente objetivo tiene un local |
| Contabilidad completa | El sistema registra la operación; no reemplaza al contador |
| Multi-tenant en una base | Cada cliente tiene su instalación y su base. Es más simple y más seguro |
| Facturación electrónica en línea | No existe obligatoriedad para el segmento objetivo y rompería el modelo offline |
