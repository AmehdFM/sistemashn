# Operación, instalador, respaldos y actualizaciones: plan de área

**Meta:** distribuir Repuestos por negocio y recuperar una instalación real después de errores, migraciones o fallas de actualización. **Depende de:** Core y flujos comerciales. **Spec:** `docs/superpowers/specs/2026-09-25-sistemashn-python-design.md`.

## Tareas

- [ ] **Instalador por rubro.** Construcción reproducible de Repuestos para Windows, sin secretos privados incluidos; separar binarios/datos, rutas de usuario y permisos. Personalizar nombre/logo/licencia al primer arranque, no recompilar por cliente. Probar instalación/actualización/desinstalación conservando datos y arranque sin internet en equipo objetivo.
- [ ] **Respaldo manual.** Crear copia consistente mediante API de SQLite, registrar fecha, destino y verificación; permitir mismo disco como opción inicial y recomendar USB/disco externo. Recordatorios visibles y persistidos que se disparan cuando la PC vuelve a encenderse. Probar copia durante actividad, disco lleno, destino desconectado y archivo corrupto.
- [ ] **Restauración.** Confirmar negocio, versión de esquema y compatibilidad, guardar punto previo, restaurar en ensayo, verificar integridad/arranque y registrar auditoría. No reemplazar base activa si falla verificación. Probar backup antiguo y recuperación tras fallo a mitad.
- [ ] **Paquete de actualización.** Manifiesto con versión, hashes y firma; verificar clave pública antes de extraer o ejecutar, impedir rutas fuera de destino y downgrade no aprobado. Fuente por internet o selección manual de ZIP. Actualizador separado espera transacción activa, respalda base, reemplaza programa, migra, comprueba arranque y revierte binario/base juntos al fallar. Probar firma inválida, paquete truncado, corte y migración fallida.
- [ ] **Actualización normal y obligatoria.** Normal: aviso y elección del administrador. Obligatoria: orden remota autenticada que puede ejecutarse sin aprobación local tras concluir la operación activa; aviso insistente mientras espera. Equipo offline recibe orden solo al reconectar. Definir canal, identidad de instalación, firma/antirreplay y gestión de claves antes de codificar. Probar orden falsa, repetida, desconexión y venta en curso sin interrumpirla.
- [ ] **Aceptación.** Ejecutar el recorrido del plan general y prueba en Windows 4 GB/HDD con ~1,000 productos y jornadas próximas a 100 ventas; registrar tiempos, memoria, errores de impresión y restauración en máquina de ensayo. Manual breve para activación, respaldo, restauración, actualización y soporte; documentar reactivación por hardware.

## Evidencia de salida

Dos rutas verificadas de actualización (red y ZIP), obligatoria firmada que espera fin de venta, reversión completa tras fallo inducido, respaldo externo y en mismo disco restaurados en ensayo, licencia perpetua funcional offline e instalador reproducible. No publicar a clientes si alguna recuperación o migración destruye datos o deja estados incompatibles.
