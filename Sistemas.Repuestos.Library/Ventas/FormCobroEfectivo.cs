using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;

namespace Sistemas.Repuestos.Library.Ventas
{
    // Calculadora de cambio: el cajero cuenta billete por billete pulsando
    // los botones de denominación (cada click SUMA al monto recibido) o
    // escribe el monto a mano. El vuelto que se ve aquí es puramente visual
    // — se recalcula en cada cambio para retroalimentar al cajero mientras
    // todavía está contando, pero nunca se manda al servidor: el valor que
    // efectivamente queda grabado en la venta lo calcula sp_RegistrarVenta,
    // y es ese el que se usa después para el recibo. Este formulario solo
    // expone EfectivoRecibido.
    public sealed class FormCobroEfectivo : FormBase
    {
        // Billetes y monedas de Lempira vigentes.
        private static readonly decimal[] Denominaciones =
            { 500m, 200m, 100m, 50m, 20m, 10m, 5m, 2m, 1m, 0.50m, 0.20m, 0.10m };

        private readonly decimal _total;
        private readonly NumericUpDown _numRecibido;
        private readonly Label _lblVuelto;
        private readonly Button _btnConfirmar;

        public decimal EfectivoRecibido { get; private set; }

        public FormCobroEfectivo(decimal total)
        {
            _total = total;

            Text = Textos.Pos.CobroEfectivoTitulo;
            ClientSize = new Size(440, 460);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var pnlContenido = new Panel { Dock = DockStyle.Fill, Padding = new Padding(UiTheme.Espacio.Xl) };

            // El total es la tipografía más grande de toda pantalla de
            // captura (guía UI/UX §7.3) — es el dato que el cajero necesita
            // ver primero y más grande mientras cuenta el efectivo.
            var lblTotal = new Label
            {
                Text = string.Format(Textos.Pos.CobroEfectivoTotalFormato, total),
                Dock = DockStyle.Top,
                Height = 40,
                Font = new Font(UiTheme.FuenteTitulo.FontFamily, 20f, FontStyle.Bold),
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };

            var pnlRecibido = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                WrapContents = false,
                Margin = new Padding(0, 0, 0, UiTheme.Espacio.Lg)
            };
            var lblCampoRecibido = new Label { Text = Textos.Pos.CobroEfectivoCampoRecibido, AutoSize = true, Margin = new Padding(0, UiTheme.Espacio.Sm, UiTheme.Espacio.Sm, 0) };
            _numRecibido = new NumericUpDown { Width = 160, Height = UiTheme.Medidas.AlturaControl, DecimalPlaces = 2, Maximum = 999999, Minimum = 0, Margin = new Padding(0, 0, UiTheme.Espacio.Sm, 0) };
            _numRecibido.ValueChanged += (s, e) => ActualizarVuelto();
            var btnLimpiar = Botones.CrearSecundario(Textos.Pos.CobroEfectivoBotonLimpiar);
            btnLimpiar.Click += (s, e) => _numRecibido.Value = 0;
            pnlRecibido.Controls.AddRange(new Control[] { lblCampoRecibido, _numRecibido, btnLimpiar });

            // Fila de botones de denominación: 500/200/100/50/20/10/5/2/1
            // (billetes) y 1/0.50/0.20/0.10 (monedas), en una grilla que
            // envuelve — cada click suma esa denominación al monto recibido,
            // como cuando el cajero cuenta el dinero.
            var pnlDenominaciones = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = true,
                AutoScroll = true
            };
            foreach (var denominacion in Denominaciones)
            {
                var boton = new Button
                {
                    Text = "L. " + denominacion.ToString("0.##"),
                    Size = new Size(88, 36),
                    Margin = new Padding(UiTheme.Espacio.Xs)
                };
                boton.Click += (s, e) => { _numRecibido.Value = Math.Min(_numRecibido.Maximum, _numRecibido.Value + denominacion); };
                pnlDenominaciones.Controls.Add(boton);
            }

            _lblVuelto = new Label
            {
                Dock = DockStyle.Bottom,
                Height = 30,
                Font = new Font(UiTheme.FuenteBase, 14f, FontStyle.Bold),
                Margin = new Padding(0, UiTheme.Espacio.Lg, 0, UiTheme.Espacio.Sm)
            };

            _btnConfirmar = Botones.CrearPrimario(Textos.Pos.CobroEfectivoBotonConfirmar);
            _btnConfirmar.Dock = DockStyle.Bottom;
            _btnConfirmar.AutoSize = false;
            _btnConfirmar.Height = UiTheme.Medidas.AlturaControl + 4;
            _btnConfirmar.Click += BtnConfirmar_Click;

            pnlContenido.Controls.Add(_lblVuelto);
            pnlContenido.Controls.Add(_btnConfirmar);
            pnlContenido.Controls.Add(pnlRecibido);
            pnlContenido.Controls.Add(lblTotal);
            pnlContenido.Controls.Add(pnlDenominaciones);
            Controls.Add(pnlContenido);

            ActualizarVuelto();
        }

        // Único cálculo del lado C# en todo este flujo, y es puramente
        // visual: retroalimenta al cajero mientras todavía está contando el
        // dinero. Nunca se envía al servidor — sp_RegistrarVenta vuelve a
        // calcular el vuelto real con el total que él mismo determina.
        private void ActualizarVuelto()
        {
            var vuelto = _numRecibido.Value - _total;
            _lblVuelto.Text = string.Format(Textos.Pos.CobroEfectivoVueltoFormato, vuelto);
            _lblVuelto.ForeColor = vuelto < 0 ? UiTheme.Error : UiTheme.Exito;
            _btnConfirmar.Enabled = _numRecibido.Value >= _total;
        }

        private void BtnConfirmar_Click(object? sender, EventArgs e)
        {
            EfectivoRecibido = _numRecibido.Value;
            DialogResult = DialogResult.OK;
            Close();
        }
    }
}
