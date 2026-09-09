using System.Globalization;
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
            // Punto y coma fijos (convención hondureña, igual que en-US) sin
            // depender del locale de Windows de cada máquina cliente — se usa
            // DefaultThreadCurrentCulture (no solo CurrentThread.CurrentCulture)
            // para que los hilos de threadpool (continuaciones async/Dapper)
            // también lo hereden. en-US no tiene efecto colateral de moneda
            // porque el sistema nunca formatea con "C", solo "N2"/"N0".
            var cultura = CultureInfo.GetCultureInfo("en-US");
            CultureInfo.DefaultThreadCurrentCulture = cultura;
            CultureInfo.DefaultThreadCurrentUICulture = cultura;

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
