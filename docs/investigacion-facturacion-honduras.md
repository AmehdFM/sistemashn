# Investigación: autoimpresión de facturas en Honduras

Fecha de revisión: 2026-09-25. Alcance: sistema de escritorio local para un negocio de repuestos. Este documento orienta el diseño; antes de activar facturación fiscal para un cliente se debe verificar su autorización concreta y la normativa aplicable en ese momento.

## Resultado principal

El Reglamento del Régimen de Facturación (Acuerdo 481-2017 y reformas) distingue la modalidad **autoimpresor** de la modalidad por imprenta. Los sistemas computarizados son un medio de autoimpresión: el obligado tributario emite con software propio o adquirido. La facturación electrónica, definida como otro medio, implica interacción simultánea con sistemas de la Administración Tributaria para obtener el CAEE. Para el producto offline, la ruta a estudiar es *autoimpresor por sistema computarizado*, no afirmar que se integra a emisión electrónica del SAR. [Reglamento, arts. 4.22, 4.29, 47, 50-54](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf).

Cada negocio obligado debe estar inscrito en el régimen y en la modalidad correspondiente. Para sistema computarizado, registra el sistema, establecimiento y puntos de emisión. La autorización de impresión y vigencia se solicita al SAR para cada sistema y tipo de documento y establece un rango correlativo; no basta instalar SistemasHN ni escribir manualmente un CAI. [Reglamento, arts. 45, 47, 59 y 61](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf). El SAR publica una [guía de solicitud para imprenta y autoimpresor 2026](https://www.sar.gob.hn/download/ayuda-solicitud-de-autorizacion-de-impresion-por-imprenta-y-auto-impresor-2025/), actualizada en julio de 2026; hay que contrastar el trámite concreto antes de instruir al cliente.

## Requisitos que afectan el software

| Tema | Hallazgo | Consecuencia de diseño |
|---|---|---|
| Integración y auditoría | El sistema computarizado debe estar integrado al menos a contabilidad o inventario, tener seguridad/auditoría y preservar información actual e histórica disponible de inmediato. También debe generar archivos de texto para traslado a la Administración por servicios web o intercambio de protocolo. [Art. 53](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf) | Inventario, usuarios, auditoría e historial inmutable son parte de la capacidad fiscal. Definir y probar exportación de datos fiscales; no prometer integración en línea si no está especificada. |
| Autorización | Hay CAI, fecha límite, rango y correlativo fiscal por punto/tipo autorizados; la autorización por autoimpresor computarizado es por sistema y tipo. [Arts. 10, 59, 61-62](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf) | Modelo separado de autorizaciones y series; validar rango, fecha y tipo antes de emitir, impedir reuso. El número interno de venta siempre existe y nunca reemplaza al correlativo fiscal. |
| Formato de factura | El art. 10 enumera RTN y datos del emisor, CAI, límite, rango y correlativo fiscal de 16 dígitos `NNN-NNN-NN-NNNNNNNN` (01 para factura). El art. 11 enumera datos del cliente, líneas e impuestos según el caso. [Arts. 10-11](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf) | Plantilla fiscal distinta del comprobante interno; tomar instantánea de datos al emitir. Revisar texto consolidado y reformas antes de fijar campos o umbrales definitivos. |
| Fecha de emisión | Para bienes, el art. 14 vincula emisión a entrega o pago/otorgamiento de crédito, lo que suceda primero. [Art. 14](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf) | Cotización y apartado no son por sí una factura fiscal; revisar anticipos y momento de entrega en casos reales. |
| Correcciones | El art. 41 exige anular documentos con error, conservar original/copia y orden cronológico. La nota de crédito es documento complementario con autorización, numeración y referencia a factura original. [Arts. 25-26, 41](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf) | No borrar facturas; devolución comercial y corrección fiscal son flujos vinculados, con nota de crédito cuando proceda. Determinar supuestos y trámites con asesoría tributaria antes de automatizar. |
| Contingencia | El art. 55 contempla documentos preimpresos autorizados ante fallas del autoimpresor; operar sin emitirlos puede generar sanción. [Art. 55](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf) | Documentar procedimiento de contingencia y posterior conciliación; un recibo interno no sustituye comprobante fiscal. |

El SAR indica que quienes transfieran bienes o presten servicios deben emitir comprobante fiscal y enumera factura, ticket y notas de crédito entre los documentos. Por tanto, la opción de **comprobante genérico** del producto debe quedar rotulada y almacenada como documento *interno, no fiscal*; no se debe presentar como factura autorizada ni utilizarla como sustituto de la obligación fiscal del negocio. [Página oficial de facturación](https://www.sar.gob.hn/facturacion/).

## Decisiones pendientes antes de implementar la emisión fiscal

1. Verificar el **texto consolidado y reformas aplicables en 2026**, especialmente detalles del art. 11, y cualquier disposición posterior, con SAR o asesor tributario; la página oficial [publica reglamento y reformas](https://www.sar.gob.hn/facturacion/). Este análisis usa el texto 481-2017 y las páginas actuales del SAR; no certifica que todos los campos y umbrales originales permanezcan idénticos.
2. Obtener un caso de autorización real de un negocio de prueba, sin exponer datos sensibles: modalidad, sistema, establecimiento, punto, tipos de documento, CAI, rangos y vencimiento. Diseñar la configuración y validación según ese caso.
3. Confirmar con SAR si hay requisitos de registro, identificación técnica o declaración jurada del software que deba preparar el proveedor. El art. 53 menciona declaración jurada del obligado tributario antes de autorizar autoimpresor.
4. Precisar formato/protocolo de exportación de archivos de texto y si existe una obligación operativa adicional para el rubro. No inferir un API de validación en tiempo real para autoimpresor.
5. Verificar con asesoría tributaria cómo documentar devoluciones parciales, cambios, reembolsos y anulaciones con notas de crédito, y cómo conservar copia fiscal en soporte térmico/PDF.

## Reglas para la primera implementación

- Registrar venta interna y su ID siempre; manejar documentos fiscales en entidad y secuencia separadas.
- Deshabilitar **Emitir factura fiscal** si el negocio no configuró autorización válida o se agotó/venció el rango; no permitir que el administrador fuerce una emisión fuera de rango.
- Guardar snapshot y copia reproducible del documento emitido, usuario, fecha, CAI, número fiscal, rango, impuestos y referencia a la transacción.
- Mostrar alertas anticipadas de vencimiento y agotamiento, pero no renovar automáticamente una autorización que corresponde solicitar al negocio ante el SAR.
- Mantener ventas, devoluciones y notas con historial y auditoría, además de respaldos y restauración verificables.

## Fuentes primarias

- [SAR: Facturación y normativa publicada](https://www.sar.gob.hn/facturacion/).
- [Secretaría de Finanzas, Acuerdo 481-2017, copia en Tribunal Superior de Cuentas](https://www.tsc.gob.hn/web/leyes/Acuerdo_No_481_2017.pdf).
- [SAR: texto consolidado del reglamento y reformas](https://www.sar.gob.hn/download/texto-consolidado-reglamento-del-regimen-de-facturacion-otros-documentos-fiscales-y-registro-fiscal-de-imprentas-contenido-en-el-acuerdo-481-2017-segun-acuerdos-609-2017-725-2018-y-817-2018/).
- [SAR: guía de autorización de impresión por imprenta y autoimpresor 2026](https://www.sar.gob.hn/download/ayuda-solicitud-de-autorizacion-de-impresion-por-imprenta-y-auto-impresor-2025/).
- [SAR: criterio sobre documentos emitidos con errores](https://www.sar.gob.hn/helpie_faq/que-hacer-en-caso-de-emitir-un-documento-fiscal-con-errores-en-el-llenado/).
