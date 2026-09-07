using System.Collections.Generic;
using System.Linq;

namespace Sistemas.Core.UI.Dashboard
{
    // Lista estática de módulos disponibles en el Dashboard. Cada vertical
    // (Repuestos, y las que sigan) llama Registrar(...) con sus propios
    // módulos ANTES de abrir FormDashboardBase, sin necesitar modificar
    // Sistemas.Core.UI.
    public static class DashboardModuleRegistry
    {
        private static readonly List<IDashboardModule> _modulos = new();

        public static IReadOnlyList<IDashboardModule> Modulos => _modulos.OrderBy(m => m.Orden).ToList();

        public static void Registrar(IDashboardModule modulo) => _modulos.Add(modulo);

        // Los dos módulos fijos de Core. Se registran una sola vez, antes
        // del primer login — llamarlo más de una vez duplicaría las entradas.
        public static void RegistrarModulosBase()
        {
            Registrar(new MenuDashboardModule());
            Registrar(new AjustesDashboardModule());
        }
    }
}
