using System.Windows.Forms;

namespace Sistemas.Repuestos.Library.Cuentas
{
    public sealed class CuentasControl : UserControl
    {
        public CuentasControl()
        {
            Dock = DockStyle.Fill;

            var tabs = new TabControl { Dock = DockStyle.Fill };

            var tabCobrar = new TabPage(Textos.Cuentas.TabPorCobrar);
            tabCobrar.Controls.Add(new CuentasPorCobrarPanel());

            var tabPagar = new TabPage(Textos.Cuentas.TabPorPagar);
            tabPagar.Controls.Add(new CuentasPorPagarPanel());

            tabs.TabPages.AddRange(new[] { tabCobrar, tabPagar });
            Controls.Add(tabs);
        }
    }
}
