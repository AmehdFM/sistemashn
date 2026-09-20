# Checklist de QA visual, interacción y accesibilidad

## 1. Preparación

- [ ] Compilar `SistemasHN.slnx` sin errores ni advertencias nuevas.
- [ ] Ejecutar `scripts/validar-ui.ps1` sin hallazgos no justificados.
- [ ] Usar textos cortos/largos, tildes, cero, montos grandes, activos/inactivos y dos páginas.
- [ ] Probar con datos, resultado vacío, filtro sin resultados y error recuperable.
- [ ] Registrar versión, commit, resolución, DPI y pantalla.

## 2. Matriz de entorno

| Resolución | Escala | Resultado |
|---|---:|---|
| 1366×768 | 100 % | Flujo completo sin scroll horizontal de página. |
| 1366×768 | 125 % | Sin texto/botones cortados; scroll solo en contenido. |
| 1920×1080 | 100 % | Contenido no pierde legibilidad por estiramiento. |
| 1920×1080 | 150 % | Controles escalan y conservan alineación. |

Con dos monitores:

- [ ] Mover la ventana entre DPI distintos.
- [ ] Confirmar recálculo de fuentes/controles.
- [ ] Confirmar diálogos dentro del monitor activo.

## 3. Shell y navegación

- [ ] Sidebar 220 px expandido y 56 px colapsado a 100 %.
- [ ] Orden: Inicio, POS, Caja, Ventas; Inventario, Compras, Clientes, Proveedores; Ajustes.
- [ ] Grupos claros sin exceso de separadores.
- [ ] Activo identificable sin depender solo del color.
- [ ] Hover diferente de activo.
- [ ] Cada icono colapsado tiene tooltip y nombre accesible.
- [ ] Usuario y cerrar sesión siguen accesibles colapsado.
- [ ] Solo módulos hacen scroll; encabezado/pie permanecen.
- [ ] Navegación repetida no duplica módulos ni handlers.
- [ ] Título de contenido coincide con módulo activo.

## 4. Jerarquía visual

- [ ] Un único título de página.
- [ ] Títulos de sección consistentes.
- [ ] Una acción primaria domina el flujo activo.
- [ ] Acento no se usa como decoración.
- [ ] Éxito, advertencia, error e información usan rol correcto.
- [ ] Jerarquía de superficies usa tono/borde, no sombra.
- [ ] 4–8 px une elementos inseparables.
- [ ] 12–16 px separa controles del grupo.
- [ ] 24–32 px separa secciones.
- [ ] No hay huecos arbitrarios ni amontonamiento.

## 5. Formularios

- [ ] Etiquetas/campos alineados.
- [ ] Campos usan ancho semántico según dato.
- [ ] Año/porcentaje no ocupa todo el ancho.
- [ ] Nombre/correo/dirección/búsqueda tienen espacio.
- [ ] Obligatorio no depende solo del color.
- [ ] Primer campo inválido recibe foco.
- [ ] Error junto al campo explica cómo corregir.
- [ ] Contenido se conserva tras error.
- [ ] Guardar se deshabilita durante operación y restaura en `finally`.
- [ ] Cancelar/Escape protege trabajo según contexto.
- [ ] Tab sigue orden visual y de negocio.

## 6. Botones, iconos y ayuda

- [ ] Texto usa verbo específico.
- [ ] Primario/secundario/terciario/destructivo distinguibles.
- [ ] Destructiva separada de Guardar.
- [ ] Deshabilitado conserva contexto y explica causa si hace falta.
- [ ] Iconos accionables mínimo 32×32.
- [ ] Solo-icono tiene tooltip y `AccessibleName`.
- [ ] No hay `+` o `?` ambiguos.
- [ ] Ayuda recibe foco y abre con Enter/Espacio.
- [ ] Tooltip breve; texto largo usa explicación extendida.
- [ ] Ayudas viven en `Textos.cs`.

## 7. Tablas y listas

- [ ] Encabezado, toolbar, filtros, grilla/estado y paginación en orden.
- [ ] Una columna flexible absorbe sobrante.
- [ ] Texto izquierda; números/dinero derecha.
- [ ] Fechas/estados consistentes.
- [ ] Filas uniformes, sin wrap.
- [ ] Texto truncado ofrece tooltip.
- [ ] Enter y doble clic hacen lo mismo.
- [ ] Acción de fila deshabilitada sin selección.
- [ ] Recarga conserva selección si aún existe.
- [ ] No se actúa sobre selección obsoleta.
- [ ] Extremos de paginación se deshabilitan, no ocultan.
- [ ] Página, rango y total correctos.

## 8. Estados

- [ ] Cargando impide acciones incompatibles sin congelar shell.
- [ ] Vacío inicial explica y permite crear.
- [ ] Vacío por filtro permite limpiar.
- [ ] Error es accionable y permite reintentar.
- [ ] Datos anteriores se marcan desactualizados tras error.
- [ ] Volver a datos limpia mensaje/acción anterior.

## 9. POS y transacciones

- [ ] Total y acción final permanecen visibles.
- [ ] Flujo completo sin mouse.
- [ ] Atajos críticos visibles, por ejemplo `Cobrar (F12)`.
- [ ] Enter no agrega/cobra dos veces.
- [ ] Quitar requiere selección válida.
- [ ] Caja cerrada presenta Abrir caja como única primaria.
- [ ] Crédito muestra cliente/plazo claramente.
- [ ] Error de stock conserva carrito y captura.
- [ ] Total, recibido y vuelto alineados.
- [ ] Cancelar cobro restaura foco correcto.

## 10. Importaciones

- [ ] Secuencia Plantilla→Archivo→Previsualización→Importar evidente.
- [ ] Ruta larga se trunca con tooltip sin empujar botones.
- [ ] Archivo inválido produce mensaje accionable.
- [ ] Filas válidas/fallidas tienen texto además de color.
- [ ] Resumen indica importadas y fallidas.
- [ ] Reintento respeta reglas y no duplica silenciosamente.

## 11. Accesibilidad y teclado

- [ ] Todo accionable recibe foco visible.
- [ ] Tab/Shift+Tab sin ciclos ni saltos.
- [ ] Enter confirma solo donde corresponde.
- [ ] Escape cancela/cierra según contexto.
- [ ] Ctrl+F enfoca búsqueda.
- [ ] F5 recarga sin perder filtros.
- [ ] F12 cobra y está visible.
- [ ] Labels se relacionan con control.
- [ ] Estado no depende solo del color.
- [ ] Información indispensable es accesible sin mouse.

## 12. Texto y localización

- [ ] Español de Honduras y textos en `Textos.cs`.
- [ ] Misma acción usa el mismo término.
- [ ] Sin SQL, excepciones o nombres internos.
- [ ] Montos `N2`; cantidades mediante `CantidadFormatter`.
- [ ] RTN, CAI e ISV conservan nomenclatura.
- [ ] Texto largo no se corta a 150 %.

## 13. Rendimiento y estabilidad

- [ ] Carga no congela shell.
- [ ] Cambio de módulo sin parpadeo excesivo.
- [ ] Redimensionar no recrea consultas/controles.
- [ ] Grillas no calculan ancho por todo el contenido.
- [ ] Navegar 30 veces no duplica eventos ni controles.
- [ ] Cerrar diálogo durante async no produce excepción tardía.

## 14. Registro por pantalla

```text
Pantalla:
Commit evaluado:
Datos utilizados:
Resoluciones y DPI:
Estados cubiertos:
Recorrido de teclado:
Hallazgos corregidos:
Excepciones justificadas:
Responsable/revisor:
Fecha:
```

## 15. Cierre del programa

- [ ] Toda fila está Conforme o tiene deuda explícita.
- [ ] Validador UI termina con código 0.
- [ ] Solución compila sin errores ni advertencias nuevas.
- [ ] No hay referencias Core→vertical.
- [ ] No se agregaron dependencias.
- [ ] Se recorrieron caminos de error de `docs/07-estrategia-de-pruebas.md`.
- [ ] Guía, roadmap y código describen el mismo estado.

