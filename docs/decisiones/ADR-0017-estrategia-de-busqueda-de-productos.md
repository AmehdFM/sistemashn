# ADR-0017 — Estrategia de búsqueda de productos

- **Estado:** 🔴 **ABIERTA** — se resuelve con datos, no con suposiciones
- **Urgencia:** al medir con el catálogo real del primer cliente
- **Origen:** decisión D-2 de [`plan-desarrollo-base-datos.md`](../../plan-desarrollo-base-datos.md) §10

## Contexto

`sp_ListarProductos` busca con `LIKE '%texto%'`. Un comodín inicial **impide
usar el índice**: SQL Server hace un scan de la tabla en cada tecleo.

En SQL Server Express, con 1 GB de buffer pool y un disco mecánico, ese scan
tiene un techo. Dónde está exactamente ese techo depende del tamaño real del
catálogo, y **eso no se sabe todavía**: no hay ningún cliente en producción.

## Opciones

| Opción | Ventaja | Costo |
|---|---|---|
| **(a) Aceptar el `LIKE '%...%'`** | Cero trabajo. El comportamiento es el que el usuario espera: encuentra el texto en cualquier parte del nombre | Scan en cada búsqueda. Viable hasta unos 5 000 productos; más allá hay que medir |
| **(b) Búsqueda por prefijo `LIKE 'texto%'`** | Usa el índice. Rápido a cualquier escala | **Cambia el comportamiento esperado**: buscar `aceite` ya no encuentra `Filtro de aceite`. Para un catálogo de repuestos es un retroceso serio de usabilidad |
| **(c) Full-Text Search** | Rápido, con búsqueda por palabras y no por subcadena. Express lo soporta | Agrega un componente a instalar y configurar en cada cliente, con un modo de fallo más que atender por teléfono |

**Recomendación: (a) por ahora.** Medir con el catálogo real del primer cliente
y decidir con datos. Si hace falta cambiar, **(c)** conserva la usabilidad;
**(b)** la sacrifica y debería ser el último recurso.

## Qué medir en el primer cliente

- Cantidad real de productos en el catálogo cargado.
- Tiempo de respuesta de una búsqueda con el peor caso (una letra sola).
- Si el usuario percibe la demora al teclear.

Con esos tres datos la decisión se toma sola. Sin ellos, cualquier optimización
es adivinanza — y la opción (b) es una que se paga en ventas perdidas.

## Nota

Esta decisión interactúa con [ADR-0016](ADR-0016-collation-acento-insensitiva.md):
si se adopta Full-Text Search, la configuración de idioma del catálogo full-text
también hay que definirla, y no es la misma cosa que la collation.
