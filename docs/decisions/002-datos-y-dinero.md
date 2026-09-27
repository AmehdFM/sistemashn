# ADR-002: representación de datos, dinero e ISV

Fecha: 2026-09-26 · Estado: aceptada

## Tipos exactos
En Python todo importe, costo o cantidad es `decimal.Decimal`. En SQLite se guardan como `INTEGER` escalado mediante
`TypeDecorator` de SQLAlchemy (`sistemashn.core.db.types`):

| Tipo | Escala | Uso |
|---|---|---|
| `Money` | 10² (centavos) | precios, totales, pagos, saldos (Lempiras) |
| `UnitCost` | 10⁴ | costo unitario y costo promedio ponderado |
| `Quantity` | 10³ | cantidades (fraccionarias solo si la unidad lo permite) |
| `Rate` | 10⁴ | tasas (ISV 0.15 → 1500) |

Al guardar se cuantiza con `ROUND_HALF_UP` a la escala; un valor con más decimales se redondea en el servicio,
no silenciosamente en la base: los helpers `money()`, `unit_cost()`, `qty()` de `sistemashn.core.money` cuantizan
explícitamente. `float` está prohibido (el `TypeDecorator` lanza `TypeError` si lo recibe).

## ISV
Tasas por producto: exento 0 %, 15 %, 18 %. Ajuste de negocio `precios_incluyen_isv` (por defecto `True`). El
cálculo por línea: si incluye, `base = round(total / (1 + tasa), 2)` e `impuesto = total - base`. Los totales de
documento suman por tasa (gravado 15 %, gravado 18 %, exento, ISV 15 %, ISV 18 %). Redondeo por línea.

## SQLite
Por conexión: `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=FULL`, `busy_timeout=5000`. Una sesión por
tarea/hilo; `UnitOfWork` reintenta hasta 3 veces con espera creciente ante `database is locked` solo si la transacción
no alcanzó a confirmar. Claves: `id INTEGER` autoincremental; documentos además `uuid` texto único.
Fechas en UTC (`DateTime(timezone=True)` guardado como ISO); la UI muestra hora de Honduras (UTC-6).

## Ubicación de datos
`%LOCALAPPDATA%\SistemasHN\<vertical>\` (base `sistemashn.db`, `backups\`, `logs\`, `documentos\`), sobreescribible con
variable `SISTEMASHN_DATA_DIR` o argumento `--data-dir` (pruebas y ensayo). Nunca dentro del directorio del programa.
