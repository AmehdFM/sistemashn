# ADR-0005 — Licenciamiento offline con firma RSA atada a la máquina

- **Estado:** Aceptada
- **Fecha:** 2026-09-09 (documenta una decisión anterior, vigente desde el inicio)

## Contexto

El producto se vende con **licencia perpetua por máquina** y se instala en
lugares **sin internet**. Hace falta impedir que una copia se instale
indefinidamente en otras máquinas, sin que la validación dependa de la red y sin
que el cliente sienta que "se lo pueden apagar".

## Decisión

Activación **offline con firma asimétrica RSA**:

1. La app calcula un **código de máquina**: SHA-256 hexadecimal de
   `ProcessorId | Serie de disco | Serie de placa madre`, leídos por WMI. Si
   nada responde, cae a `Environment.MachineName`.
2. El cliente dicta ese código. El vendedor lo pega en `Sistemas.Licencias`
   —herramienta interna que **nunca se distribuye**— y genera una clave firmada
   con la **clave privada**, con vigencia opcional.
3. La app verifica la firma con la **clave pública embebida** y que el payload
   corresponda a esta máquina.
4. La licencia válida se guarda en `%LocalAppData%\SistemasHN\license.dat`,
   cifrada con **DPAPI a nivel de máquina**: copiarla a otra PC no sirve.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Validación en línea con servidor de licencias | Rompe el requisito central: el sistema tiene que funcionar sin internet, siempre |
| Clave simétrica o algoritmo de serie | Cualquiera que desensamble el binario puede generar claves. Con RSA, el binario solo contiene la pública |
| Dongle USB | Costo por unidad, logística de envío y un puerto más que puede fallar |
| Sin protección | El producto se copia entre negocios el primer mes |

## Consecuencias

**A favor**
- Cero dependencia de red.
- El binario distribuido no permite generar licencias.
- El cliente conserva su licencia para siempre; nada se apaga solo.
- La vigencia opcional deja abierta la puerta a vender mantenimiento anual sin
  cambiar el mecanismo.

**En contra — y hay que operarlas**
- **`clave_privada.pem` es el activo crítico del negocio.** Está en
  `.gitignore`. Si se pierde, no se pueden emitir activaciones nuevas; si se
  filtra, el modelo de licenciamiento deja de existir. Necesita respaldo cifrado
  fuera de la máquina de desarrollo.
- **Cambiar el disco duro cambia el código de máquina** y exige reactivar. Es un
  caso real que hay que saber atender por teléfono.
- La activación es un paso manual en cada venta.
