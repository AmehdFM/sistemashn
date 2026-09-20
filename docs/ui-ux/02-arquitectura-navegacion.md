# Arquitectura de navegación y acceso

**Estado:** propuesta para aprobación  
**Restricción:** conserva `IDashboardModule`, `DashboardModuleRegistry` y la
separación Core/verticales

## 1. Objetivo

Organizar el shell según la frecuencia y el flujo de trabajo de una tienda, sin
convertir Core en conocedor de la vertical ni introducir reglas de permisos que
el dominio aún no define.

## 2. Problemas del orden actual

El orden actual mezcla:

- un lanzador duplicado (`Menú`);
- entidades maestras (`Inventario`, `Clientes`, `Proveedores`);
- operaciones (`Compras`, `POS`, `Caja`);
- historial (`Ventas`);
- administración (`Ajustes`).

La secuencia no cuenta una historia de trabajo. El usuario que inicia una venta
debe pasar visualmente por módulos menos frecuentes antes de llegar a POS.

## 3. Modelo propuesto

El sidebar tendrá tres zonas conceptuales:

### 3.1 Operación principal

1. **Inicio**
2. **Punto de venta**
3. **Caja**
4. **Ventas**

POS es la tarea de mayor frecuencia. Caja y Ventas se mantienen cerca porque
pertenecen al mismo ciclo operativo.

### 3.2 Gestión

5. **Inventario**
6. **Compras**
7. **Clientes**
8. **Proveedores**

Inventario y Compras forman el flujo de abastecimiento. Clientes y Proveedores
permanecen separados en esta etapa porque ya son módulos distintos y fusionarlos
alteraría más que la presentación. Una futura entrada "Terceros" solo deberá
considerarse mediante una decisión funcional independiente.

### 3.3 Utilidades

9. **Ajustes**
10. **Ayuda**, cuando exista contenido útil y offline
11. **Usuario y cerrar sesión**, en el pie

Ajustes se separa visualmente de los módulos operativos y permanece cerca del
pie. No se mezcla con el orden numérico de la vertical.

## 4. Inicio en lugar de Menú

`MenuDashboardModule` evolucionará a un módulo de Inicio. La primera versión no
inventará indicadores sin una fuente de datos. Puede contener:

- accesos rápidos a POS, nueva compra, nuevo producto y nuevo tercero;
- estado real de caja abierta/cerrada;
- alertas reales disponibles, como CAI o stock mínimo, cuando los servicios ya
  las expongan de forma eficiente;
- accesos recientes si pueden mantenerse sin infraestructura compleja.

La cuadrícula de todos los módulos deja de ser el contenido principal porque el
sidebar ya cumple esa función. Mientras el tablero operativo se implementa, el
lanzador existente puede mantenerse como transición bajo el nombre Inicio, con
orden y jerarquía mejorados.

## 5. Contrato de registro sin romper arquitectura

`IDashboardModule` seguirá siendo el contrato de las verticales. La evolución
debe ser compatible y centrada en metadatos genéricos. El diseño necesita poder
expresar:

- zona o grupo de navegación;
- orden dentro del grupo;
- acción frecuente opcional;
- texto accesible del icono;
- disponibilidad para la sesión actual cuando ya exista una regla real.

Core define el concepto genérico de grupo; cada vertical decide dónde ubica sus
módulos. Core no pregunta si un módulo es POS, inventario o repuestos.

Los módulos existentes deben seguir funcionando durante la migración. Si se
extiende la interfaz, el plan deberá usar una estrategia que evite romper todas
las verticales en un único cambio no verificable, por ejemplo valores por
defecto o un contrato de metadatos separado.

## 6. Comportamiento del sidebar

### 6.1 Expandido

- ancho de 220 px;
- marca/nombre del negocio en el encabezado cuando exista;
- grupo visible mediante espacio y, si hace falta, etiqueta secundaria;
- icono de 48 px de región y texto alineado;
- activo con fondo diferenciado e indicador adicional al color;
- hover neutro;
- texto truncado con elipsis solo como último recurso.

### 6.2 Colapsado

- ancho de 56 px;
- iconos centrados;
- tooltip obligatorio con nombre del módulo;
- indicador activo visible;
- el pie de usuario se convierte en un acceso con icono y tooltip, no desaparece
  sin alternativa;
- el botón de expandir/colapsar conserva nombre accesible y foco.

### 6.3 Persistencia

El estado expandido/colapsado puede persistirse localmente solo si utiliza la
infraestructura de configuración ya disponible y no introduce dependencia. No
es requisito de la primera fase.

### 6.4 Scroll

La lista de módulos debe desplazarse si una vertical futura supera la altura
disponible. El encabezado y el pie permanecen visibles. En 1366×768 no deben
quedar opciones inaccesibles.

## 7. Encabezado del área de contenido

Cada módulo presenta dentro del contenido:

- título de página;
- descripción breve solo cuando aporta contexto;
- ruta o botón Volver en flujos internos;
- acción principal alineada consistentemente;
- estado contextual cuando corresponda.

El nombre del módulo en el sidebar no sustituye el título de página. El usuario
debe entender dónde está aunque el sidebar esté colapsado.

## 8. Iconografía

Se conserva Segoe MDL2 Assets según ADR-0011.

Reglas:

- un concepto mantiene el mismo glifo en sidebar, Inicio y acciones relacionadas;
- no se usan emojis ni caracteres que dependan de otra fuente;
- cada glifo tiene texto accesible;
- un icono decorativo no recibe foco;
- un icono accionable tiene objetivo mínimo de 32×32 px;
- el color no cambia el significado básico del icono;
- antes de agregar un glifo se verifica su disponibilidad en las versiones de
  Windows soportadas.

El plan incluirá un catálogo central documentado para evitar que dos módulos
usen glifos iguales con significados distintos.

## 9. Acceso y permisos

La sesión actual distingue al administrador, pero no existe un contrato general
de permisos por módulo. Por eso esta fase:

- conserva la visibilidad actual de módulos;
- conserva las restricciones administrativas ya implementadas dentro de las
  pantallas;
- no oculta módulos basándose en nombres de rol inventados;
- permite que el contrato futuro consulte disponibilidad sin acoplar Core a una
  vertical.

Ocultar módulos por rol será una fase funcional separada cuando exista una
matriz de permisos autorizada. La UI nunca será la única barrera de seguridad.

## 10. Navegación y ciclo de vida

Se conserva un único shell con una región de contenido. Al cambiar de módulo:

1. el ítem activo se actualiza;
2. la vista saliente libera recursos y suscripciones;
3. se crea o recupera la vista según la política documentada;
4. la vista entra en estado de carga sin congelar el shell;
5. el foco pasa al título o primer control operativo;
6. un error de carga ofrece Reintentar y permite seguir navegando.

La política inicial seguirá siendo crear y disponer vistas, como hace
`FormDashboardBase`, salvo pantallas transaccionales donde perder estado pueda
destruir trabajo del usuario. Esas excepciones deberán advertir antes de salir
o mantener un borrador explícito; no se resolverán mediante caché global
indiscriminada.

## 11. Atajos de navegación

- `Ctrl+1` o acceso equivalente a Inicio solo si no entra en conflicto con
  captura de datos.
- `Ctrl+F` pertenece a la búsqueda de la pantalla actual.
- `F5` actualiza la pantalla actual.
- `Alt` más tecla de acceso puede usarse en elementos con texto cuando WinForms
  lo soporte claramente.
- El plan no asignará una combinación distinta a cada módulo hasta validar que
  los usuarios realmente la necesitan.

## 12. Criterios de aceptación

- El orden visual refleja Operación, Gestión y Utilidades.
- POS es accesible sin recorrer catálogos menos frecuentes.
- Ajustes y sesión están separados de la operación.
- Cada icono colapsado se identifica por tooltip y accesibilidad.
- El módulo activo se reconoce sin depender únicamente del color.
- Todos los módulos son alcanzables a 1366×768.
- Cambiar de módulo no deja controles o suscripciones huérfanos.
- Una vertical futura puede registrar sus módulos sin modificar Core.
- No se introduce autorización basada únicamente en la UI.

