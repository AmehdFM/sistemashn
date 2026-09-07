using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Configuracion;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Common;

namespace Sistemas.Core.UI.Dashboard
{
    // Cascarón principal, compartido por todas las verticales: barra lateral
    // colapsable + panel de contenido intercambiable. Se prefiere
    // Panel+UserControls sobre MDI clásico: MDI en WinForms moderno complica
    // estilos y ciclo de vida de los controles sin aportar nada aquí.
    public class FormDashboardBase : FormBase
    {
        private const int AnchoExpandido = 220;
        private const int AnchoColapsado = 56;

        private readonly Panel _pnlSidebar;
        private readonly Panel _pnlItems;
        private readonly Panel _pnlContenido;
        private readonly Label _lblApp;
        private readonly List<SidebarItem> _items = new();
        private bool _sidebarExpandido = true;

        public FormDashboardBase(SessionContext sesion)
        {
            Icon = BrandingAssets.IconoApp;
            WindowState = FormWindowState.Maximized;
            MinimumSize = new Size(1000, 640);

            // --- Sidebar ---
            _pnlSidebar = new Panel
            {
                Dock = DockStyle.Left,
                Width = AnchoExpandido,
                BackColor = UiTheme.SidebarFondo
            };

            var pnlHeader = new Panel
            {
                Dock = DockStyle.Top,
                Height = 50,
                BackColor = UiTheme.SidebarFondo
            };

            var btnToggle = new Label
            {
                Text = "≡",
                Font = new Font("Segoe UI", 16f, FontStyle.Bold),
                ForeColor = UiTheme.SidebarTexto,
                Size = new Size(48, 50),
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Left,
                Cursor = Cursors.Hand
            };
            btnToggle.Click += (s, e) => AlternarSidebar();

            _lblApp = new Label
            {
                Text = string.Empty,
                ForeColor = UiTheme.SidebarTexto,
                Font = new Font(Font, FontStyle.Bold),
                TextAlign = ContentAlignment.MiddleLeft,
                Dock = DockStyle.Fill
            };

            pnlHeader.Controls.Add(_lblApp);
            pnlHeader.Controls.Add(btnToggle);

            _pnlItems = new Panel { Dock = DockStyle.Fill, BackColor = UiTheme.SidebarFondo };

            _pnlSidebar.Controls.Add(_pnlItems);
            _pnlSidebar.Controls.Add(pnlHeader);

            // --- Barra superior (usuario / cerrar sesión) ---
            // El Location de estos controles se fija aquí mismo, ANTES de
            // agregarlos al árbol de controles y usando solo el ancho propio
            // de cada control (medido por AutoSize) — nunca el ancho del
            // panel contenedor. WinForms no repinta un Location asignado más
            // tarde (p.ej. en el evento Load) para un hijo de un panel
            // Dock=Top, así que alinear "a la derecha" contra un ancho de
            // ventana todavía no definido no es fiable; alinear "desde la
            // izquierda" con anchos ya conocidos sí lo es.
            var pnlTopBar = new Panel { Dock = DockStyle.Top, Height = 48, BackColor = Color.White };

            var lblUsuario = new Label
            {
                Text = $"{sesion.NombreCompleto}  ·  {sesion.NombreRol}",
                ForeColor = UiTheme.TextoOscuro,
                AutoSize = true,
                Location = new Point(24, 15)
            };

            var llCerrarSesion = new LinkLabel { Text = Textos.Dashboard.BotonCerrarSesion, AutoSize = true };
            llCerrarSesion.Click += (s, e) => CerrarSesion();
            llCerrarSesion.Location = new Point(lblUsuario.Right + 24, 16);

            pnlTopBar.Controls.Add(lblUsuario);
            pnlTopBar.Controls.Add(llCerrarSesion);

            // --- Contenido ---
            _pnlContenido = new Panel { Dock = DockStyle.Fill, BackColor = UiTheme.FondoContenido };

            var pnlMain = new Panel { Dock = DockStyle.Fill };
            pnlMain.Controls.Add(_pnlContenido);
            pnlMain.Controls.Add(pnlTopBar);

            Controls.Add(pnlMain);
            Controls.Add(_pnlSidebar);

            Load += FormDashboardBase_Load;
        }

        private async void FormDashboardBase_Load(object? sender, EventArgs e)
        {
            try
            {
                var config = await ConfiguracionService.ObtenerAsync();
                var nombre = config.Existe ? config.NombreComercial ?? string.Empty : string.Empty;
                Text = nombre;
            }
            catch
            {
                // Sin nombre comercial disponible, se deja el encabezado vacío
                // en vez de mostrar la marca del creador dentro de la operación.
            }

            // Se agrega en orden INVERSO a propósito: en un panel con varios
            // hijos Dock=Top, el ÚLTIMO agregado queda más cerca del borde
            // superior (no el primero) — así el orden visual de arriba hacia
            // abajo termina coincidiendo con el Orden ascendente de cada
            // módulo, igual que ya lo hace el lanzador de "Menú".
            foreach (var modulo in DashboardModuleRegistry.Modulos.Reverse())
            {
                var item = new SidebarItem(modulo);
                item.Seleccionado += (s, ev) => NavegarAModulo(modulo);
                _items.Insert(0, item);
                _pnlItems.Controls.Add(item);
            }

            var primero = DashboardModuleRegistry.Modulos.FirstOrDefault();
            if (primero != null) NavegarAModulo(primero);
        }

        private void NavegarAModulo(IDashboardModule modulo)
        {
            foreach (var item in _items)
                item.MarcarActivo(item.Modulo == modulo);

            // Controls.Clear() no libera los controles removidos: hay que
            // disponerlos explícitamente o cada navegación deja handles y
            // controles hijos huérfanos en memoria.
            foreach (Control controlSaliente in _pnlContenido.Controls)
                controlSaliente.Dispose();
            _pnlContenido.Controls.Clear();

            var vista = modulo.CrearVista();
            vista.Dock = DockStyle.Fill;

            if (vista is ModuleLauncherControl launcher)
                launcher.ModuloSeleccionado += (s, m) => NavegarAModulo(m);

            _pnlContenido.Controls.Add(vista);
        }

        private void AlternarSidebar()
        {
            _sidebarExpandido = !_sidebarExpandido;
            _pnlSidebar.Width = _sidebarExpandido ? AnchoExpandido : AnchoColapsado;
            _lblApp.Visible = _sidebarExpandido;
            foreach (var item in _items)
                item.MostrarTexto(_sidebarExpandido);
        }

        private void CerrarSesion()
        {
            if (!Confirmar(Textos.Dashboard.ConfirmarCerrarSesion)) return;
            SessionContext.Cerrar();
            DialogResult = DialogResult.Retry; // Señal para Program.cs: volver a mostrar Login.
            Close();
        }
    }
}
