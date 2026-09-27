# Etapa 0 — validación en Windows

| Prueba | Estado | Evidencia / observación |
|---|---|---|
| Build x64 con `flet build windows` (Flutter 3.44.8 gestionado por Flet, VS 2022) | Pasa | `build/flutter/build/windows/x64/runner/Release/sistemashn.exe`, 153 MB en carpeta. Python embebido 3.14.7. |
| Salida del comando en consola cp1252 | Falla menor | `flet build` aborta al imprimir "√" al final aunque el ejecutable ya se generó. Ejecutar con `PYTHONIOENCODING=utf-8` (ver `scripts/build_windows.ps1`, Fase 6). |
| Arranque (5 corridas, PC de desarrollo) | Pasa | Ventana visible en 0.65 s promedio; working set 147 MB, privada 121 MB. `docs/validation/mediciones/stage0-dev-latitude7490.json`. El tiempo mide la ventana Flutter, no la app Python lista; repetir con la app completa. |
| Base SQLite, WAL, BEGIN IMMEDIATE, rutas con espacios/acentos | Pasa (pytest en Windows) | `tests/core/db` |
| Respaldo consistente con escritura concurrente y restauración de ensayo | Pasa (pytest) | `tests/core/operations/test_backup.py`, `test_restore.py` |
| Actualización ZIP con reversión de programa + base | Pasa (pytest) | `tests/core/operations/test_probe_update.py`, ADR-003 |
| PDF carta y 80 mm con acentos | Pasa | `docs/validation/muestras/` (fuente Arial del sistema) |
| Impresión física | No probado | Sin impresora; `print_pdf` usa la impresora predeterminada y degrada sin error. |
| Equipo objetivo 4 GB / HDD | No probado | Lo ejecuta el dueño en otros equipos con `scripts/measure_stage0.ps1`. |
| Instalador Inno Setup y updater PyInstaller | Pendiente | Fase 6. |

**Decisión:** Viable para continuar (condicionado a la medición del dueño en equipo 4 GB/HDD).
