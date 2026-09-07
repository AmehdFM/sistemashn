-- Numeración interna de ventas cuando Configuracion.FacturacionLegalActiva
-- está apagado — el negocio todavía no exige (o no tiene) un CAI vigente.
-- No compite con Facturacion.ConfiguracionCAI.CorrelativoActual: son dos
-- numeraciones independientes, nunca se mezclan en la misma factura.
CREATE SEQUENCE Repuestos.SeqVentaInterna
    AS BIGINT
    START WITH 1
    INCREMENT BY 1
    NO CYCLE;
GO
