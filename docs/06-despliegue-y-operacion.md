# 06 — Despliegue y operación

> ⚠️ **No hay ningún cliente en producción todavía.** Este documento describe el
> despliegue **objetivo** y qué falta para poder ejecutarlo. Lo que está
> implementado se marca 🟢; lo que no, 🔴.

---

## 1. Qué se instala en la máquina del cliente

| Componente | Estado |
|---|---|
| SQL Server Express + la base `SistemasHN` | 🔴 sin instalador |
| El ejecutable de la vertical y sus DLL | 🔴 sin empaquetar |
| `%ProgramData%\SistemasHN\appsettings.json` con el connection string | 🟢 la app ya lo lee de ahí |
| Tarea programada de respaldo | 🔴 `Sistemas.Mantenimiento` es un stub |

**Nunca se instala en el cliente:** `Sistemas.Licencias`. Es la herramienta del
vendedor y contiene (o requiere) la clave privada de firma.

## 2. Instalación limpia — procedimiento objetivo

1. **SQL Server Express.** Instancia nombrada `SQLEXPRESS`, autenticación de
   Windows, protocolo TCP/IP habilitado solo si habrá una segunda terminal.
2. **Base de datos.** Publicar el DACPAC de `Sistemas.Core.Database` y luego el
   de la vertical. El `Script.PostDeployment.sql` siembra roles y unidades de
   medida, y es idempotente.
   > ⚠️ **La collation se fija acá y ya no se cambia** sin migrar todo. Ver
   > [ADR-0016](decisiones/ADR-0016-collation-acento-insensitiva.md). Es la
   > decisión de instalación más costosa de revertir.
3. **Aplicación.** Copiar la carpeta publicada. Requiere el runtime de .NET 10
   Desktop, que debe empaquetarse o publicarse *self-contained* — no se puede
   contar con descargarlo en el sitio.
4. **Configuración.** Crear `%ProgramData%\SistemasHN\appsettings.json` con el
   connection string real.
5. **Primer arranque.** La app corre sola la secuencia de arranque:
   **Activación → Primer usuario → Datos del negocio → Login**.
6. **Activación de licencia.** El cliente lee su código de máquina en pantalla;
   el vendedor lo pega en `Sistemas.Licencias`, genera la clave y se la dicta.
7. **Respaldo.** Configurar la tarea programada. 🔴 Bloqueado por B1.
8. **Verificación.** Recorrer la checklist de
   [`07-estrategia-de-pruebas.md`](07-estrategia-de-pruebas.md) §3 en la máquina
   real, no en la de desarrollo.

## 3. Actualización de un cliente existente

El escenario que hay que resolver bien: **decenas de instalaciones offline, sin
personal técnico en el sitio.**

Estrategia objetivo:

1. **La base se actualiza por DACPAC**, que compara el esquema y genera solo el
   diferencial. `Configuracion.VersionEsquema` registra qué versión tiene esa
   instalación.
2. **Respaldo completo obligatorio antes de aplicar**, verificado, no asumido.
3. **La app se actualiza reemplazando la carpeta.** Sin estado en el directorio
   de instalación, así que es seguro.
4. **La app valida al arrancar** que la versión de esquema que espera coincide
   con la de la base, y se niega a operar si no. Un binario nuevo contra un
   esquema viejo corrompe datos en silencio, que es el peor de los fallos.

Reglas para que esto sea posible:
- **Ningún cambio de esquema destructivo sin script de migración de datos.**
  Renombrar una columna en SSDT genera `DROP` + `ADD`: se pierde el dato.
- **Toda columna nueva `NOT NULL` necesita `DEFAULT`**, o el despliegue falla
  contra una tabla con filas.
- **Cada release incrementa `VersionEsquema`.**

## 4. Respaldo y recuperación 🔴

Esto es lo más importante que falta. Requisitos de
`Sistemas.Mantenimiento` cuando se implemente:

- **Respaldo completo diario** a una ruta configurable, idealmente en otro
  disco físico o una USB. Un respaldo en el mismo disco no protege del fallo
  más común.
- **Registro de cada intento en `Configuracion.HistorialRespaldos`**, con éxito
  o fracaso, vía `sp_RegistrarResultadoRespaldo`.
- **Retención por antigüedad**, para no llenar el disco.
- **Verificación con `RESTORE VERIFYONLY`.**
- **`DBCC CHECKDB` semanal.** Un corte de energía puede corromper páginas y eso
  se descubre meses después si nadie mira.
- **Purga de auditoría** vía `Auditoria.sp_PurgarAuditoria`: la base tiene un
  techo de 10 GB y `Auditoria` es la única tabla que crece sin límite.
- **Visible para el usuario.** El cliente tiene que poder ver "último respaldo:
  ayer 11:00 PM · correcto" sin abrir nada técnico.

> **Un respaldo que nunca se restauró no es un respaldo.** El procedimiento de
> restauración debe probarse antes de la primera instalación, no durante la
> primera emergencia.

## 5. Licenciamiento — operación

**Emitir una activación:**
1. El cliente lee el código de máquina en la pantalla de activación.
2. Se ejecuta `Sistemas.Licencias` con `clave_privada.pem` junto al `.exe`.
3. Se pega el código y se indica la vigencia (Enter = sin vencimiento).
4. Se le dicta o envía la clave generada al cliente.

**Reglas operativas:**
- `clave_privada.pem` **nunca** entra al repositorio (está en `.gitignore`),
  nunca se envía por correo ni chat, y debe tener respaldo cifrado fuera de la
  máquina de desarrollo. **Si se pierde, no se pueden emitir activaciones
  nuevas. Si se filtra, el modelo de licenciamiento deja de existir.**
- El código de máquina es un SHA-256 de `CPU|Disco|Placa`. **Cambiar el disco
  duro cambia el código** y exige reactivar. Es un caso real que hay que saber
  atender por teléfono.
- La licencia se guarda en `%LocalAppData%\SistemasHN\license.dat` cifrada con
  DPAPI a nivel de máquina: copiarla a otra PC no sirve de nada.

## 6. Diagnóstico en campo

Cuando el cliente llama, hoy se cuenta con:

- 🟢 `Auditoria.Auditoria` — qué hizo quién y cuándo
- 🟢 `Security.Usuarios` — intentos de login fallidos
- 🟢 `Configuracion.HistorialRespaldos` — si el respaldo corrió
- 🟢 `Configuracion.sp_VerificarEstadoSistema` — chequeo general
- 🔴 **Log de aplicación en archivo** — Serilog está referenciado pero
  `LoggerConfig.cs` está vacío. Es el bloqueador B3 de
  [`05-estado-y-roadmap.md`](05-estado-y-roadmap.md)

**Principio de diseño para el soporte telefónico:** el usuario ve un mensaje en
español y un código de referencia corto. El detalle técnico queda en auditoría o
en el log, y soporte lo pide por ese código. El usuario nunca lee un error de
SQL Server por teléfono.
