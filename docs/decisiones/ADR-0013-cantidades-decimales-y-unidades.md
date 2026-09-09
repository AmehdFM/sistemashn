# ADR-0013 — Cantidades decimales con unidades de medida

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (implementada en el commit `2517169`)

## Contexto

El diseño original manejaba el stock como `INT`, asumiendo que todo se vende por
unidad. La vertical de autorepuestos ya lo desmiente: se vende medio galón de
aceite. La vertical de ferretería lo rompe del todo: 2.5 quintales de cemento,
7.30 metros de cable, 3/4 de libra de clavos.

Corregirlo después de tener datos reales sería una migración; corregirlo antes
del primer cliente es un cambio de tipo.

## Decisión

- **Las cantidades y el stock son `DECIMAL(12,2)`**, no `INT`. Aplica a
  `Productos.StockActual`, `Productos.StockMinimo`, `VentaDetalle.Cantidad`,
  `CompraDetalle.Cantidad` y equivalentes.
- **Existe `Inventario.UnidadesMedida`** como catálogo de Core, con `Codigo`,
  `Nombre`, `Simbolo`, `Sistema` y **`PermiteFraccion`**, que distingue lo que
  puede venderse partido de lo que no.
- `Productos.UnidadMedidaId` es `NOT NULL DEFAULT 1`, y el post-despliegue
  **fuerza `Id = 1` para "Unidad"** con `SET IDENTITY_INSERT`, porque el
  `DEFAULT` es un literal simple y no una subconsulta.
- El formato en pantalla se centraliza en `CantidadFormatter`, para que una
  cantidad entera no se muestre como `12.00` cuando la unidad no admite fracción.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| `INT` y vender en la unidad más chica | Obliga al usuario a pensar en mililitros y gramos. Rompe el principio de "reconocer, no recordar" |
| `FLOAT` | Error de redondeo en cálculos de dinero. Inaceptable en facturación |
| `DECIMAL` con más de 2 decimales | Complica el cuadre contra el ISV y el redondeo de la factura. Dos decimales alcanzan para el rubro |
| Unidades como texto libre en el producto | Sin catálogo no hay conversión posible ni consistencia entre productos |

## Consecuencias

**A favor**
- El sistema soporta ferretería sin cambiar el modelo — la prueba de fuego de
  la Fase C del roadmap.
- `PermiteFraccion` permite validar en el SP que no se venda media batería.

**En contra**
- **Cuidado con la aritmética decimal:** `DECIMAL(12,2) * DECIMAL(12,2)` sube a
  escala 4 por las reglas de SQL Server. Por eso `VentaDetalle.Subtotal` lleva un
  `CAST` explícito de vuelta a `DECIMAL(12,2)`. Todo cálculo nuevo debe hacer lo
  mismo.
- La conversión entre unidades (comprar por quintal, vender por libra) **todavía
  no existe** y la va a necesitar la vertical de ferretería.
