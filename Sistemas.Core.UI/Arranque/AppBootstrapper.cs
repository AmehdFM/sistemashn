using System;
using System.Windows.Forms;
using Sistemas.Core.Licensing;
using Sistemas.Core.Security;

namespace Sistemas.Core.UI.Arranque
{
    // Orquesta la secuencia de arranque (Activación → Primer usuario → Datos
    // del negocio → Login) dentro de UNA sola FormArranque, reutilizable por
    // cualquier vertical. Cada paso es un UserControl que solo avanza al
    // siguiente cuando dispara su evento de éxito; si el usuario cierra la
    // ventana en cualquier punto, EjecutarHastaLogin devuelve false.
    public static class AppBootstrapper
    {
        public static bool EjecutarHastaLogin()
        {
            using var form = new FormArranque();
            var completado = false;

            void MostrarLogin()
            {
                var paso = new LoginStepControl();
                paso.SesionIniciada += (s, e) =>
                {
                    completado = true;
                    form.DialogResult = DialogResult.OK;
                    form.Close();
                };
                form.MostrarPaso(paso);
            }

            void MostrarDatosNegocio(int usuarioId)
            {
                var paso = new DatosNegocioStepControl(usuarioId);
                paso.DatosGuardados += (s, e) => MostrarLogin();
                form.MostrarPaso(paso);
            }

            // async void a propósito: para cuando se llama, el Form de arranque
            // ya existe (aunque no se haya mostrado), y construir un Form
            // instala un SynchronizationContext de WinForms en el hilo actual.
            // Bloquear ese hilo con GetAwaiter().GetResult() aquí produce un
            // interbloqueo permanente: la continuación de la tarea necesita
            // volver a ese mismo contexto, pero nada bombea su bucle de
            // mensajes todavía porque form.ShowDialog() no se ha llamado. Con
            // await real, la continuación queda pendiente y se resuelve en
            // cuanto ShowDialog() arranca el bucle de mensajes justo después.
            async void MostrarPrimerUsuarioSiHaceFalta()
            {
                bool existenUsuarios;
                try
                {
                    existenUsuarios = await AuthService.ExistenUsuariosAsync();
                }
                catch (Exception ex)
                {
                    MessageBox.Show(form,
                        Textos.Arranque.ErrorConexionMensaje + ex.Message,
                        Textos.Arranque.ErrorConexionTitulo, MessageBoxButtons.OK, MessageBoxIcon.Error);
                    form.DialogResult = DialogResult.Cancel;
                    form.Close();
                    return;
                }

                if (existenUsuarios)
                {
                    MostrarLogin();
                    return;
                }

                var paso = new PrimerUsuarioStepControl();
                paso.UsuarioCreado += (s, usuarioId) => MostrarDatosNegocio(usuarioId);
                form.MostrarPaso(paso);
            }

            void MostrarActivacionSiHaceFalta()
            {
                if (ActivationService.TryLoadSavedLicense(out _))
                {
                    MostrarPrimerUsuarioSiHaceFalta();
                    return;
                }

                var paso = new ActivacionStepControl();
                paso.Activado += (s, e) => MostrarPrimerUsuarioSiHaceFalta();
                form.MostrarPaso(paso);
            }

            MostrarActivacionSiHaceFalta();
            form.ShowDialog();

            return completado && SessionContext.Current != null;
        }
    }
}
