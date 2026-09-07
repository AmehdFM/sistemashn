using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library.Dashboard;

namespace Sistemas.Repuestos.Library
{
    // Único punto de entrada que Sistemas.Repuestos (el .exe) necesita
    // conocer de esta librería — ver la nota de arquitectura del plan:
    // el exe nunca referencia los módulos concretos directamente.
    public sealed class RepuestosModuleProvider : IVerticalModuleProvider
    {
        public void RegistrarModulos()
        {
            DashboardModuleRegistry.Registrar(new InventarioDashboardModule());
            DashboardModuleRegistry.Registrar(new ProveedoresDashboardModule());
            DashboardModuleRegistry.Registrar(new ComprasDashboardModule());
            DashboardModuleRegistry.Registrar(new PosDashboardModule());
            DashboardModuleRegistry.Registrar(new VentasDashboardModule());
        }
    }
}
