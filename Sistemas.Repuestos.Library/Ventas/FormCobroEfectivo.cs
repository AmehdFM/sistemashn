using System;
using System.Drawing;
using System.Windows.Forms;
using Sistemas.Core.UI;
using Sistemas.Core.UI.Common;

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
            ClientSize = new Size(420, 400);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent;

            var lblTotal = new Label
            {
                Text = string.Format(Textos.Pos.CobroEfectivoTotalFormato, total),
                AutoSize = true,
                Font = new Font(UiTheme.FuenteBase, 13f, FontStyle.Bold),
                Location = new Point(20, 16)
            };

            var lblCampoRecibido = new Label { Text = Textos.Pos.CobroEfectivoCampoRecibido, AutoSize = true, Location = new Point(20, 56) };
            _numRecibido = new NumericUpDown { Location = new Point(20, 76), Size = new Size(160, 28), DecimalPlaces = 2, Maximum = 999999, Minimum = 0 };
            _numRecibido.ValueChanged += (s, e) => ActualizarVuelto();

            var btnLimpiar = new Button { Text = Textos.Pos.CobroEfectivoBotonLimpiar, Location = new Point(190, 76), Size = new Size(100, 28) };
            btnLimpiar.Click += (s, e) => _numRecibido.Value = 0;

            // Fila de botones de denominación: 500/200/100/50/20/10/5/2/1
            // (billetes) y 1/0.50/0.20/0.10 (monedas), en una grilla de 5
            // columnas que envuelve — cada click suma esa denominación al
            // monto recibido, como cuando el cajero cuenta el dinero.
            var pnlDenominaciones = new FlowLayoutPanel
            {
                Location = new Point(20, 116),
                Size = new Size(380, 190),
                FlowDirection = FlowDirection.LeftToRight,
                WrapContents = true,
                AutoScroll = true
            };
            foreach (var denominacion in Denominaciones)
            {
                var boton = new Button
                {
                    Text = "L. " + denominacion.ToString("0.##"),
                    Size = new Size(84, 34),
                    Margin = new Padding(4)
                };
                boton.Click += (s, e) => { _numRecibido.Value = Math.Min(_numRecibido.Maximum, _numRecibido.Value + denominacion); };
                pnlDenominaciones.Controls.Add(boton);
            }

            _lblVuelto = new Label
            {
                AutoSize = true,
                Font = new Font(UiTheme.FuenteBase, 14f, FontStyle.Bold),
                Location = new Point(20, 316)
            };

            _btnConfirmar = new Button
            {
                Text = Textos.Pos.CobroEfectivoBotonConfirmar,
                Location = new Point(20, 354),
                Size = new Size(380, 34),
                BackColor = UiTheme.Primario,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };
            _btnConfirmar.FlatAppearance.BorderSize = 0;
            _btnConfirmar.Click += BtnConfirmar_Click;

            Controls.AddRange(new Control[]
            {
                lblTotal, lblCampoRecibido, _numRecibido, btnLimpiar,
                pnlDenominaciones, _lblVuelto, _btnConfirmar
            });

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
