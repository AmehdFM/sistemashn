namespace Sistemas.Core.UI.Dashboard
{
    // Contrato que cada vertical implementa UNA sola vez, en una única clase,
    // para exponer sus módulos al Dashboard sin que el exe (raíz de
    // composición) necesite conocer cada clase de módulo individualmente.
    // Mantiene Program.cs idéntico entre verticales: solo cambia qué
    // IVerticalModuleProvider se instancia.
    public interface IVerticalModuleProvider
    {
        void RegistrarModulos();
    }
}
