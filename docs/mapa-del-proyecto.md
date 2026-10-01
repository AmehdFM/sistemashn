# Mapa del proyecto: dónde encontrar cada cosa

Este documento no explica el diseño del sistema (eso está en `docs/README.md` y los planes de
`docs/superpowers/plans/`); es una guía rápida de **navegación**: qué carpeta/archivo tocar según
lo que necesites hacer.

## "Necesito hacer X, ¿dónde está?"

| Necesito... | Está en... |
|---|---|
| Correr la app en mi PC | `evn\Scripts\python.exe src\main.py` |
| Correr la app con datos de prueba aislados | `.\scripts\dev.ps1 run` |
| Compilar el ejecutable Windows y ZIP | `.\scripts\dev.ps1 build` (deja el resultado en `build\`) |
| Empaquetar el proceso de actualización | `scripts\build_updater.bat` |
| Armar el instalador final (.exe de instalación) | `installer\sistemashn.iss` (con Inno Setup, en Windows) |
| Correr las pruebas automatizadas | `.\scripts\dev.ps1 test` |
| Generar un código de activación de prueba | `activar_licencia.py` (raíz del repo, solo desarrollo) |
| Firmar licencias/actualizaciones (solo el vendedor) | `tools\vendor\vendedor.py` |
| Manual para el dueño del negocio/cajero | `docs\manual-operacion.md` |
| Ver qué se hizo en cada fase del desarrollo | `docs\validation\progreso.md` |
| Entender por qué se construyó algo de cierta forma | `docs\superpowers\plans\fase-*.md` (un archivo por fase) y `docs\decisions\` (decisiones técnicas puntuales, ADRs) |
| Historial de cambios de la base de datos | `src\sistemashn\migrations\versions\` (un archivo por cambio, en orden: `0001_...`, `0002_...`, etc.) |
| Investigación legal de facturación en Honduras | `docs\investigacion-facturacion-honduras.md` |

## Estructura general (raíz del repositorio)

```
src/            El código de la aplicación (ver detalle más abajo).
tests/          Pruebas automatizadas. Refleja la misma estructura de carpetas que src/:
                la prueba de "src/sistemashn/comercial/ventas/service.py" está en
                "tests/comercial/ventas/test_service.py".
docs/           Documentación: planes de cada fase, decisiones técnicas, manuales,
                investigación legal, registro de progreso.
scripts/        Archivos .bat para tareas del día a día (pruebas, compilar, etc.).
installer/      El instalador de Windows (Inno Setup).
tools/vendor/   Herramienta EXCLUSIVA del vendedor (para firmar licencias/actualizaciones).
                Nunca se instala en la PC de un cliente.
evn/            El entorno virtual de Python. No se edita a mano: se genera con los
                comandos de "Instalación" en README.md.
build/          Se genera al compilar (scripts\dev.ps1 build / build_updater.bat).
                No es parte del código fuente; se puede borrar y volver a generar siempre.
```

## `src/sistemashn/`: las tres capas del sistema

El código está organizado en capas, de lo más genérico a lo más específico:

- **`core/`** — todo lo que no sabe nada de "vender repuestos" ni de ningún negocio en
  particular: usuarios, permisos, licencia, respaldos, actualización del programa, la base de
  datos, el asistente de primer arranque, y las pantallas de administración (Usuarios,
  Auditoría, Ajustes, Respaldos, Licencia). Es la base que reutilizaría cualquier vertical
  futura (Ferretería, Clínica, etc.), no solo Repuestos.
- **`comercial/`** — el motor de negocio genérico: catálogo, inventario, compras, ventas,
  cotizaciones, caja, crédito, devoluciones, reportes. Tampoco sabe nada de repuestos
  específicamente: sirve para "un negocio que vende productos", sea cual sea el rubro.
- **`repuestos/`** — la extensión propia del rubro de repuestos: número de parte,
  equivalencias entre piezas, catálogo de vehículos y compatibilidad. Se apoya en `comercial/`
  (un repuesto sigue siendo un producto normal de catálogo) y le agrega lo específico del rubro.
- **`app/`** — la composición final: junta `core` + `comercial` + `repuestos` en un programa que
  realmente arranca. `app/bootstrap.py` arma todos los servicios; `app/repuestos.py` es el punto
  de entrada de "SistemasHN Repuestos" en concreto (si mañana existe "SistemasHN Ferretería",
  sería otro archivo aquí, reutilizando `core`/`comercial` sin tocarlos).
- **`migrations/`** — historial de cambios de la base de datos (Alembic), separado de `core`
  porque migrations describe cómo *evolucionó* el esquema con el tiempo, no cómo es hoy (eso
  está en los modelos de cada módulo).
- **`updater/`** — el proceso de actualización, un programa APARTE del programa principal (por
  diseño: no puede reemplazarse a sí mismo mientras corre). Vive fuera de `core`/`comercial`
  porque no es parte de la app que usa el cajero, es una herramienta de mantenimiento.

Dos archivos sueltos en `src/` (no dentro de `src/sistemashn/`) son los puntos de arranque reales
de cada programa: `src/main.py` (la app) y `src/updater_main.py` (el actualizador) — existen
aparte porque así lo necesita el empaquetado (PyInstaller/Flet), que quiere un único archivo de
entrada bien simple.

### Dentro de `core/`

| Carpeta | Qué contiene |
|---|---|
| `authorization/` | Permisos y perfiles (quién puede hacer qué) |
| `identity/` | Usuarios, inicio de sesión, recuperación de contraseña |
| `audit/` | Historial de acciones, no se puede borrar ni editar |
| `db/` | Motor de la base de datos SQLite, transacciones, tipos exactos para dinero |
| `documents/` | Generación de documentos PDF (motor genérico, sin datos de venta) |
| `licensing/` | Activación offline y validación de la licencia |
| `modules/` | El "contrato" que sigue cada módulo para registrar sus permisos/pantallas |
| `operations/` | Respaldo y restauración de la base de datos |
| `updater/` | Verificación de firma de los paquetes de actualización |
| `settings/` | Datos del negocio (nombre, logo) y ajustes de operación configurables |
| `setup/` | El asistente de primer arranque |
| `ui/` | Pantallas y piezas visuales compartidas: tema, barra lateral, y las pantallas propias de Core (Usuarios, Auditoría, Ajustes, Respaldos, Licencia) |

### Dentro de `comercial/`

| Carpeta | Qué contiene |
|---|---|
| `catalogo/` | Productos, categorías, unidades, kits |
| `inventario/` | Entradas, salidas y reservas de stock |
| `contrapartes/` | Clientes y proveedores |
| `compras/` | Compras a proveedor |
| `ventas/` | Ventas (motor detrás del punto de venta) |
| `cotizaciones/` | Cotizaciones y apartados |
| `caja/` | Apertura/cierre de caja y sus movimientos |
| `credito/` | Cuentas por cobrar y por pagar (un solo motor para ambas) |
| `pagos/` | Métodos de pago compartidos |
| `devoluciones/` | Devoluciones de cliente y a proveedor |
| `documentos/` | Comprobantes PDF de venta/compra |
| `fiscal/` | Factura fiscal (CAI) — apagada por defecto, ver el manual de operación |
| `reportes/` | Reportes y exportación a Excel |
| `ui/` | Todas las pantallas de lo anterior, incluido el punto de venta (`pos_view.py`) |

### Dentro de `repuestos/`

| Carpeta | Qué contiene |
|---|---|
| `partes/` | Número de parte y equivalencias entre productos |
| `vehiculos/` | Catálogo de vehículos y qué piezas les sirven |
| `ui/` | Pantallas propias de este rubro |
