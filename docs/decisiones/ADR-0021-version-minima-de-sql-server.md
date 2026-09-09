# ADR-0021 — Versión mínima de SQL Server a soportar

- **Estado:** 🔴 **ABIERTA** — requiere definición del negocio
- **Urgencia:** antes de empaquetar el instalador
- **Origen:** decisión D-6 de [`plan-desarrollo-base-datos.md`](../../plan-desarrollo-base-datos.md) §10

## Contexto

Los `.sqlproj` declaran hoy `DSP` = **`Sql170DatabaseSchemaProvider`**, es decir
SQL Server 2022. Ese valor no se eligió: es el que puso la herramienta por ser
la versión más nueva disponible en la máquina de desarrollo.

Eso importa porque el `DSP` determina **contra qué versión valida SSDT** y qué
características del motor se permiten. Si un cliente tiene una versión anterior,
el DACPAC puede fallar al desplegarse o, peor, usar sintaxis que esa versión no
entiende.

## Qué hay que decidir

**La versión más baja que se va a instalar en un cliente real**, no la más nueva
disponible en desarrollo.

Preguntas que la determinan:
1. ¿El instalador va a incluir SQL Server Express, o se usa el que el cliente
   ya tenga?
2. Si se incluye: ¿qué versión se empaqueta? ¿Cuánto pesa la descarga? ¿Cuáles
   son sus requisitos de sistema operativo?
3. Si no se incluye: ¿qué versión se exige como mínimo, y qué hace el sistema
   cuando encuentra una anterior?
4. ¿Qué versión de Windows corren realmente las máquinas del mercado objetivo?
   Las versiones recientes de SQL Server no instalan en Windows viejo.

## Compromiso

| Versión más baja soportada | Ventaja | Costo |
|---|---|---|
| Más nueva (2022) | Sintaxis moderna disponible; mejor rendimiento | Excluye máquinas con Windows viejo, que son parte real del mercado objetivo |
| Más antigua (2016/2017/2019) | Instala en más máquinas | Sintaxis y características limitadas al mínimo común |

## Consecuencias de la decisión

Una vez elegida, hay que:
1. Fijar el `DSP` de **ambos** `.sqlproj` a esa versión.
2. Recompilar y verificar que todo el DDL y todos los SP siguen siendo válidos.
3. Documentar el requisito en la guía de instalación.
4. Hacer que la app lo verifique al arrancar, para dar un mensaje claro en vez de
   fallar de forma confusa.

## Nota

Esta decisión y [ADR-0016](ADR-0016-collation-acento-insensitiva.md) se aplican
al mismo archivo y conviene resolverlas juntas: ambas exigen recompilar los
`.sqlproj` y reconstruir la base de desarrollo desde cero.
