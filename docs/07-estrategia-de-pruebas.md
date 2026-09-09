# 07 — Estrategia de pruebas

> **Estado honesto: no existe ninguna prueba automatizada en este repositorio.**
> No hay proyecto de tests en `SistemasHN.slnx` ni CI configurado. Toda
> verificación es manual. Este documento describe cómo se verifica hoy y qué
> estrategia adoptar cuando se automatice.

---

## 1. Cómo se verifica un cambio hoy

1. `dotnet build SistemasHN.slnx` compila sin errores ni advertencias nuevas.
2. Publicar los proyectos SSDT contra una base local limpia.
3. Ejecutar `dotnet run --project Sistemas.Repuestos` y recorrer a mano el flujo
   afectado.
4. Recorrer la checklist de §3 correspondiente al área tocada.

**Antes de dar por terminado un cambio, exigite:**
- ¿Probaste el camino de error, no solo el feliz? (producto inexistente, stock
  insuficiente, CAI agotado, campo vacío)
- ¿Probaste con la base vacía? El primer arranque es un camino real que se rompe
  seguido.
- ¿El mensaje que ve el usuario está en español y es accionable?

## 2. Qué hay que probar, por orden de riesgo

El riesgo se mide en **cuánto le cuesta al cliente si falla**, no en cuánto
cuesta escribir la prueba.

### 🔴 Crítico — dinero e inventario
Un fallo acá le cuesta dinero real al cliente y destruye su confianza.

- `sp_RegistrarVenta` — cálculo de subtotal/ISV/total, descuento de stock,
  correlativo CAI, generación de CxC al crédito
- `sp_AnularVenta` — devolución de stock, correlativo quemado, estado consistente
- `sp_RegistrarCompra` — entrada de stock, generación de CxP
- `sp_ArmarPaquete` y la venta de un paquete — descuento del stock de componentes
- `sp_RegistrarPagoCuentaPorCobrar` / `...PorPagar` — saldo nunca negativo ni
  mayor que el original
- `sp_ObtenerCorrelativoCAI` — nunca entrega el mismo número dos veces

### 🟠 Alto — concurrencia y durabilidad
Es lo que el entorno del cliente garantiza que va a ocurrir.

- **Dos cajas vendiendo el último artículo a la vez.** Una debe ganar y la otra
  recibir un mensaje claro. Nunca stock negativo, nunca correlativo duplicado.
- **Corte de energía en medio de una venta.** Al volver, la venta existió
  completa o no existió: nunca a medias.
- **La plantilla C-5 anidada.** Un SP interno que falla dentro de otro debe
  revertir solo lo suyo y dejar viva la transacción externa.

### 🟡 Medio — seguridad y licencias
- Login correcto e incorrecto; el hash BCrypt verifica y el intento se registra
- Clave de activación válida, con firma alterada, de otra máquina, vencida
- Un usuario no administrador no accede a lo que no le toca

### 🟢 Bajo — presentación
- Formato de números y moneda con distintos locales de Windows
- Paginación en los límites (primera página, última, cero filas)
- Importación de Excel con archivo malformado, columnas cambiadas, filas malas

## 3. Checklist manual antes de una entrega

**Arranque**
- [ ] Base vacía: la app pide activación, crea el primer usuario y los datos del negocio
- [ ] Clave de licencia inválida: mensaje claro, no avanza
- [ ] Login incorrecto: mensaje genérico (no revela si el usuario existe)
- [ ] Cerrar sesión vuelve al arranque sin cerrar el proceso

**Inventario**
- [ ] Crear, editar y desactivar un producto
- [ ] Código duplicado: se rechaza con mensaje claro
- [ ] Búsqueda con y sin tildes *(hoy falla sin tildes — ver ADR-0016)*
- [ ] Importar Excel: plantilla correcta, columnas cambiadas, filas malas mezcladas
- [ ] Paginación: primera, última y página vacía

**Venta**
- [ ] Venta al contado con varios productos: totales correctos, stock descontado
- [ ] Venta con producto de ISV 0 % y 15 % mezclados
- [ ] Stock insuficiente: se rechaza sin dejar nada a medias
- [ ] Venta a crédito genera la cuenta por cobrar con el saldo correcto
- [ ] Venta de un paquete descuenta el stock de los componentes
- [ ] Anular una venta al contado devuelve el stock
- [ ] Anular una venta a crédito con pagos: **debe rechazarse** hasta resolver
      [ADR-0019](decisiones/ADR-0019-anulacion-de-venta-a-credito-con-pagos.md)
- [ ] El correlativo avanza y nunca se repite
- [ ] CAI agotado o vencido: mensaje claro antes de emitir

**Compras y cuentas**
- [ ] Compra al contado suma stock
- [ ] Compra a crédito genera la cuenta por pagar
- [ ] Pago parcial deja el saldo correcto y el estado en `PagadaParcial`
- [ ] Pago total deja saldo cero y estado `Pagada`
- [ ] Pago mayor al saldo: se rechaza

**Operación**
- [ ] Cerrar la app en medio de una operación no deja datos a medias
- [ ] Con la base caída, la app muestra un mensaje entendible y no revienta

## 4. Estrategia objetivo cuando se automatice

**Prioridad: los SP antes que el C#.** Ahí está toda la regla de negocio (C-3),
ahí está el dinero, y son código puro sin UI de por medio. Un proyecto de
pruebas de C# que solo verifique DTOs no compra nada.

### Nivel 1 — Integración de stored procedures *(máximo valor)*
Un proyecto `Sistemas.Pruebas` (`net10.0`, xUnit) que:
- Crea una base temporal aplicando el DACPAC, la siembra y la destruye al final
- Ejecuta cada SP crítico contra escenarios reales y verifica el estado resultante
- Prueba explícitamente la concurrencia: dos conexiones peleando por el último
  artículo, y la anidación de la plantilla C-5

Es el nivel más caro de montar y el único que verifica lo que de verdad importa.

### Nivel 2 — Unitarias de la lógica pura de C#
Lo que no toca la base: verificación de firma de licencia, `LicensePayload`,
validación de estructura del Excel de importación, `CantidadFormatter`,
`fn_CalcularISV` en su equivalente de C#. Barato y rápido.

### Nivel 3 — Humo de arranque
Que la solución compile y que la app llegue a la pantalla de login contra una
base recién creada. Detecta el 80 % de las roturas por refactor.

**Lo que no vale la pena automatizar:** pruebas de UI de WinForms. Frágiles,
lentas y caras de mantener para lo que devuelven. La checklist manual de §3 es
mejor inversión para esta capa.

### Cuándo montar esto
No antes de resolver los bloqueadores de
[`05-estado-y-roadmap.md`](05-estado-y-roadmap.md) §3. Un cliente sin respaldo
es un riesgo mayor que un SP sin prueba automatizada. Pero **el nivel 1 debería
existir antes del segundo cliente**: a partir de ahí, un defecto en un SP de
dinero se replica en cada instalación y se descubre por teléfono.
