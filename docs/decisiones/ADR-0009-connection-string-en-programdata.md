# ADR-0009 — Connection string compartido en `ProgramData`

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

Todas las verticales instaladas en una máquina apuntan a **la misma base de
datos** ([ADR-0001](ADR-0001-core-mas-verticales-en-una-base.md)). Si cada
ejecutable llevara su propio `appsettings.json`, cambiar el servidor obligaría a
editar N archivos y cualquier olvido dejaría una app apuntando a otro lado.

A la vez, en desarrollo es incómodo tener que tocar `ProgramData` en cada F5.

## Decisión

`ConnectionFactory` busca la configuración en dos rutas, en orden, y usa la
primera que exista:

1. `%ProgramData%\SistemasHN\appsettings.json` — la ubicación real de producción
2. `AppContext.BaseDirectory\appsettings.json` — junto al ejecutable, para desarrollo

El valor se carga una sola vez (`Lazy<string>`) y cada método de servicio abre
su propia conexión con `CreateConnection()`. Las conexiones no se comparten ni
se guardan: el pool de ADO.NET ya hace ese trabajo, y una conexión viva es un
bloqueo esperando a ocurrir.

Si no aparece ninguno de los dos archivos, o `ConnectionStrings:Default` está
vacío, la app falla en el arranque con un mensaje explícito. Es correcto: sin
base de datos no hay nada que hacer.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Solo junto al ejecutable | N copias que hay que mantener sincronizadas |
| Registro de Windows | Más difícil de inspeccionar y editar por teléfono con un cliente |
| `%AppData%` del usuario | La configuración es de la máquina, no del usuario; con dos usuarios de Windows habría que configurar dos veces |

## Consecuencias

**A favor**
- Una sola configuración por máquina, aunque haya varias verticales.
- Editable con el Bloc de notas guiando al cliente por teléfono.
- Desarrollo sin fricción: alcanza con el `appsettings.json` del proyecto.

**En contra**
- Escribir en `ProgramData` requiere privilegios: es tarea del instalador.
- El archivo está en texto plano. Con autenticación integrada de Windows no hay
  credenciales que proteger; **si algún día se usara autenticación SQL, este
  archivo pasaría a ser un secreto** y habría que revisar esta decisión.
