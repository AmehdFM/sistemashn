# 08 — Flujo de trabajo con IA

Este proyecto lo desarrolla **una sola persona apoyada en asistentes de IA**.
Ese contexto define todo lo que sigue: no hay revisor humano que atrape un error
antes de que llegue al código, así que el rigor tiene que estar en el proceso.

---

## 1. El contrato de las dos partes

**Lo que la documentación te garantiza como IA:** el porqué de cada decisión
estructural ya está escrito. No tenés que deducir por qué la lógica está en SPs,
por qué la cultura es `en-US` ni por qué no hay MDI. Está en los ADRs.

**Lo que se espera de vos a cambio:**
1. **Leer antes de escribir.** `CLAUDE.md` y el documento de convenciones de la
   capa que vas a tocar.
2. **Copiar el precedente.** Casi todo tiene un gemelo en el repositorio. Una
   estructura original es, casi siempre, una falla de análisis.
3. **No resolver en silencio lo que está marcado como abierto.** Las decisiones
   ADR-0016 a ADR-0021 requieren definición del negocio. Si tu tarea depende de
   una, decilo y proponé, no asumas.
4. **Reportar la contradicción.** Si el código real contradice la documentación,
   **manda el código** y la documentación se corrige. Decilo explícitamente en
   vez de elegir en silencio.

## 2. Orden de trabajo para una tarea típica

```
1. Entender  → ¿qué capa? ¿qué precedente existe? ¿algún ADR aplica?
2. Preguntar → solo si una decisión abierta bloquea, o si hay dos lecturas
               razonables que llevan a trabajos distintos
3. Base de datos primero → la regla de negocio vive en el SP (C-3)
4. Servicio  → delgado: abre conexión, llama al SP, mapea
5. DTO       → contrato de datos, sin lógica
6. Pantalla  → siguiendo la GUIA-UI-UX y copiando una pantalla existente
7. Textos    → ningún literal suelto; todo al Textos.cs de su capa
8. Verificar → compilar y recorrer la checklist de 07-estrategia-de-pruebas.md
9. Documentar→ ¿esto cambia una decisión estructural? entonces un ADR
```

## 3. Cómo escribir una petición que salga bien a la primera

Escrito para el desarrollador. Una petición vaga produce trabajo que hay que
tirar.

**En vez de:** *"agregá descuentos a las ventas"*

**Pedí:**
> Agregar descuento por línea en la venta.
> - **Alcance:** SP `sp_RegistrarVenta`, tabla `VentaDetalle`, `VentaService`, `PosControl`.
> - **Regla:** el descuento es un porcentaje de 0 a 100 sobre el precio unitario;
>   el ISV se calcula sobre el precio ya descontado.
> - **Fuera de alcance:** descuento global sobre la factura, descuentos por cliente.
> - **Decisión ya tomada:** se guarda el porcentaje, no el monto.

Lo que hace la diferencia: **el alcance explícito, la regla de negocio concreta y
lo que queda afuera.** Sin eso, la IA elige por vos y elige mal la mitad de las
veces.

## 4. Criterios de terminado

Una tarea no está terminada hasta que **todos** se cumplen. Si alguno no se
puede cumplir, decilo explícitamente en la entrega en vez de dejarlo pasar.

**Siempre**
- [ ] `dotnet build SistemasHN.slnx` compila sin errores ni advertencias nuevas
- [ ] Ningún literal de texto visible fuera de un `Textos.cs` (R3)
- [ ] Ningún color ni fuente fuera de `UiTheme` (R3)
- [ ] Ninguna dependencia nueva sin autorización (R4)
- [ ] Core sigue sin conocer ninguna vertical (R2)
- [ ] Todo en español: código, comentarios, mensajes
- [ ] Los comentarios explican **por qué**, no **qué**

**Si tocaste SQL**
- [ ] La checklist completa de [`03-convenciones-base-datos.md`](03-convenciones-base-datos.md) §9
- [ ] El archivo está registrado en el `.sqlproj`
- [ ] Si es listado, va paginado en servidor

**Si tocaste C#**
- [ ] La regla de negocio quedó en el SP, no en el servicio (C-3)
- [ ] `using var conn = ConnectionFactory.CreateConnection();` por método
- [ ] `commandType: CommandType.StoredProcedure`, nunca SQL interpolado
- [ ] `UsuarioId` se pasa en toda operación auditable
- [ ] Nada de `.Result`, `.Wait()` ni `.GetAwaiter().GetResult()` en el hilo de UI

**Si tocaste una pantalla**
- [ ] Cumple la [`GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md`](../GUIA-UI-UX-SISTEMAS-EMPRESARIALES.md):
      rejilla de 4/8 px, jerarquía tipográfica, roles de color
- [ ] Se parece a una de las cinco pantallas canónicas (§7 de esa guía)
- [ ] Toda la captura se puede hacer sin tocar el mouse
- [ ] Los estados vacío, cargando y de error están resueltos, no solo el feliz

**Si cambiaste una decisión estructural**
- [ ] Hay un ADR nuevo o uno existente marcado como reemplazado, en el mismo commit

## 5. Qué hacer cuando algo no está claro

| Situación | Qué hacer |
|---|---|
| La respuesta está en la documentación | Usala. No vuelvas a deducirla ni la pongas en duda |
| Hay un ADR abierto que bloquea la tarea | **Preguntá.** Proponé una opción con su fundamento, pero no la apliques |
| Dos lecturas razonables llevan a trabajos distintos | **Preguntá antes de construir**, no después |
| Es una decisión rutinaria de implementación | Decidila y decí qué elegiste. No pidas permiso para nombrar una variable |
| El código contradice la documentación | Manda el código. Reportá la contradicción y corregí el documento |
| La tarea exige romper una regla dura (R1–R4) | **Detenete y preguntá.** Nunca la rompas por conveniencia |
| Falta información del negocio (una regla fiscal, un flujo del cliente) | Preguntá. No la inventes: una regla fiscal inventada llega a producción y le cuesta al cliente |

## 6. Errores frecuentes de asistentes en este repositorio

Salieron de trabajo real. Vale la pena leerlos antes de empezar.

- **Poner la validación en C# "porque es más fácil de probar".** Rompe C-3. La
  app no es la única forma de llegar a los datos.
- **Escribir el mensaje de error directo en la pantalla.** Rompe R3. Va al
  `Textos.cs` de esa capa.
- **Usar `Color.FromArgb` para "un gris nomás".** Rompe R3. Va a `UiTheme` con
  nombre de rol.
- **Agregar un paquete NuGet para algo que ya está resuelto.** Rompe R4. Antes,
  revisá `Sistemas.Core.UI`: `GridStyler`, `PaginacionControl`,
  `CantidadFormatter`, `FormBase`, `BrandingAssets`.
- **Traer la tabla completa y paginar en memoria.** Funciona con 50 productos en
  desarrollo y muere con 5 000 en la máquina del cliente.
- **Devolver `NULL` sin `CAST`.** Dapper revienta al mapear.
- **Un `ROLLBACK` a secas en un SP que puede ser anidado.** Error 3903 y
  transacción del llamador destruida.
- **Resolver una decisión abierta por cuenta propia** porque "hay que avanzar".
  Es la peor: queda enterrada en el código y se descubre con datos reales.
- **Marcar como terminado algo verificado solo en el camino feliz.** Los caminos
  de error son la mitad del trabajo en un sistema sin soporte técnico en sitio.

## 7. Documentación como parte del trabajo, no como epílogo

La razón de existir de estos documentos es que una sesión nueva de IA arranque
con contexto en vez de deducirlo. Eso solo funciona si se mantienen vivos:

- **Un ADR se escribe en el mismo commit que el código que lo implementa.** Un
  ADR escrito después es una racionalización.
- **`05-estado-y-roadmap.md` se actualiza al cerrar cada fase**, no al final.
- **Una convención se escribe cuando se rompe.** Si una revisión encuentra un
  defecto que una regla escrita habría evitado, esa regla se agrega a
  `02-convenciones-codigo.md` o `03-convenciones-base-datos.md` en ese momento.
- **Nada de "próximamente".** Si algo es un stub, se dice que es un stub.
