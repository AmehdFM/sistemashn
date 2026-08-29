CREATE FUNCTION Facturacion.fn_CalcularISV
(
    @Monto      DECIMAL(12,2),
    @TasaISV    DECIMAL(5,2)
)
RETURNS DECIMAL(12,2)
AS
BEGIN
    RETURN ROUND(@Monto * @TasaISV / 100.0, 2);
END
GO
