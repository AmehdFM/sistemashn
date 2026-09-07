using Sistemas.Core.Security;
using Sistemas.Core.UI.Arranque;
using Sistemas.Core.UI.Dashboard;
using Sistemas.Repuestos.Library;

namespace Sistemas.Repuestos
{
    internal static class Program
    {
        /// <summary>
        ///  The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
            // To customize application configuration such as set high DPI settings or default font,
            // see https://aka.ms/applicationconfiguration.
            ApplicationConfiguration.Initialize();

            // Módulos fijos de Core (Menú, Ajustes) + los propios de esta
            // vertical, expuestos a través de IVerticalModuleProvider — el
            // exe nunca conoce las clases concretas de los módulos. Se
            // registran una sola vez: no dependen de la sesión y volver a
            // registrarlos en cada vuelta del bucle los duplicaría.
            DashboardModuleRegistry.RegistrarModulosBase();
            new RepuestosModuleProvider().RegistrarModulos();

            while (true)
            {
                if (!AppBootstrapper.EjecutarHastaLogin()) return;

                using var dashboard = new FormDashboardBase(SessionContext.Current!);
                if (dashboard.ShowDialog() != DialogResult.Retry) return; // Retry = cerró sesión, vuelve al arranque.
            }
        }
    }
}
