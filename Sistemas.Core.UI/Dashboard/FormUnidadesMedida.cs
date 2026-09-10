using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Common;
using Sistemas.Core.UI.Controles;

namespace Sistemas.Core.UI.Dashboard
{
    // Catálogo de unidades de medida, abierto desde Ajustes (solo
    // administradores). Alta rápida + activar/desactivar inline, igual que
    // el manejo de Categorías en Inventario — no hay borrado físico porque
    // Productos referencia estas filas por FK.
    public sealed class FormUnidadesMedida : FormBase
    {
        private readonly BindingList<UnidadMedidaDto> _unidades = new();

        private readonly TextBox _txtCodigo;
        private readonly TextBox _txtNombre;
        private readonly TextBox _txtSimbolo;
        private readonly CheckBox _chkPermiteFraccion;
        private readonly TextBox _txtSistema;
        private readonly DataGridView _grid;
        private readonly Label _lblEstado;

        public FormUnidadesMedida()
        {
            Text = Textos.UnidadesMedida.TituloVentana;
            ClientSize = new Size(680, 480);
            StartPosition = FormStartPosition.CenterParent;
            MinimumSize = new Size(620, 420);

            var pnlTop = new Panel { Dock = DockStyle.Top, BackColor = Color.White, Padding = new Padding(UiTheme.Espacio.Lg), AutoSize = true };

            var pnlCampos = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false, Margin = new Padding(0, 0, 0, UiTheme.Espacio.Sm) };

            var grupoCodigo = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblCodigo = new Label { Text = Textos.UnidadesMedida.CampoCodigo, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoTenue };
            _txtCodigo = new TextBox { Width = 80, Height = UiTheme.Medidas.AlturaControl, Dock = DockStyle.Top, MaxLength = 10 };
            grupoCodigo.Controls.Add(_txtCodigo);
            grupoCodigo.Controls.Add(lblCodigo);

            var grupoNombre = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblNombre = new Label { Text = Textos.UnidadesMedida.CampoNombre, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoTenue };
            _txtNombre = new TextBox { Width = 180, Height = UiTheme.Medidas.AlturaControl, Dock = DockStyle.Top, MaxLength = 50 };
            grupoNombre.Controls.Add(_txtNombre);
            grupoNombre.Controls.Add(lblNombre);

            var grupoSimbolo = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblSimbolo = new Label { Text = Textos.UnidadesMedida.CampoSimbolo, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoTenue };
            _txtSimbolo = new TextBox { Width = 70, Height = UiTheme.Medidas.AlturaControl, Dock = DockStyle.Top, MaxLength = 10 };
            grupoSimbolo.Controls.Add(_txtSimbolo);
            grupoSimbolo.Controls.Add(lblSimbolo);

            var grupoSistema = new Panel { AutoSize = true, Margin = new Padding(0, 0, UiTheme.Espacio.Md, 0) };
            var lblSistema = new Label { Text = Textos.UnidadesMedida.CampoSistema, Dock = DockStyle.Top, Height = 20, ForeColor = UiTheme.TextoTenue };
            _txtSistema = new TextBox { Width = 110, Height = UiTheme.Medidas.AlturaControl, Dock = DockStyle.Top, MaxLength = 20 };
            grupoSistema.Controls.Add(_txtSistema);
            grupoSistema.Controls.Add(lblSistema);

            _chkPermiteFraccion = new CheckBox { Text = Textos.UnidadesMedida.CampoPermiteFraccion, AutoSize = true, Checked = true, Margin = new Padding(0, UiTheme.Espacio.Xl, 0, 0) };

            pnlCampos.Controls.AddRange(new Control[] { grupoCodigo, grupoNombre, grupoSimbolo, grupoSistema, _chkPermiteFraccion });

            var pnlAccion = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, WrapContents = false };
            var btnAgregar = Botones.CrearPrimario(Textos.UnidadesMedida.BotonAgregar);
            btnAgregar.Click += BtnAgregar_Click;
            _lblEstado = new Label
            {
                ForeColor = UiTheme.Error,
                AutoSize = false,
                Width = 480,
                Height = UiTheme.Medidas.AlturaControl,
                Margin = new Padding(UiTheme.Espacio.Md, 0, 0, 0)
            };
            pnlAccion.Controls.AddRange(new Control[] { btnAgregar, _lblEstado });

            pnlTop.Controls.Add(pnlAccion);
            pnlTop.Controls.Add(pnlCampos);

            _grid = new DataGridView { DataSource = _unidades };
            GridStyler.Aplicar(_grid);
            _grid.ReadOnly = false;
            _grid.AutoGenerateColumns = false;
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(UnidadMedidaDto.Codigo), HeaderText = Textos.UnidadesMedida.CampoCodigo, FillWeight = 12, ReadOnly = true });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(UnidadMedidaDto.Nombre), HeaderText = Textos.UnidadesMedida.CampoNombre, FillWeight = 28, ReadOnly = true });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(UnidadMedidaDto.Simbolo), HeaderText = Textos.UnidadesMedida.CampoSimbolo, FillWeight = 14, ReadOnly = true });
            _grid.Columns.Add(new DataGridViewTextBoxColumn { DataPropertyName = nameof(UnidadMedidaDto.Sistema), HeaderText = Textos.UnidadesMedida.CampoSistema, FillWeight = 16, ReadOnly = true });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(UnidadMedidaDto.PermiteFraccion), HeaderText = Textos.UnidadesMedida.CampoPermiteFraccion, FillWeight = 15, ReadOnly = true });
            _grid.Columns.Add(new DataGridViewCheckBoxColumn { DataPropertyName = nameof(UnidadMedidaDto.Activo), HeaderText = Textos.UnidadesMedida.CampoActivo, FillWeight = 15, ReadOnly = false });
            _grid.CellValueChanged += Grid_CellValueChanged;
            _grid.CurrentCellDirtyStateChanged += (s, e) => { if (_grid.IsCurrentCellDirty) _grid.CommitEdit(DataGridViewDataErrorContexts.Commit); };

            Controls.Add(_grid);
            Controls.Add(pnlTop);

            Load += async (s, e) => await CargarAsync();
        }

        private async System.Threading.Tasks.Task CargarAsync()
        {
            try
            {
                var unidades = await UnidadMedidaService.ListarAsync(soloActivas: false);
                _unidades.RaiseListChangedEvents = false;
                _unidades.Clear();
                foreach (var u in unidades) _unidades.Add(u);
                _unidades.RaiseListChangedEvents = true;
                _unidades.ResetBindings();
                _lblEstado.Text = string.Empty;
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.UnidadesMedida.NoSeCargaronPrefijo + ex.Message;
            }
        }

        private async void BtnAgregar_Click(object? sender, EventArgs e)
        {
            var codigo = _txtCodigo.Text.Trim();
            var nombre = _txtNombre.Text.Trim();
            var simbolo = _txtSimbolo.Text.Trim();

            if (codigo.Length == 0 || nombre.Length == 0 || simbolo.Length == 0)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.UnidadesMedida.ErrorCamposRequeridos;
                return;
            }

            var sistema = string.IsNullOrWhiteSpace(_txtSistema.Text) ? null : _txtSistema.Text.Trim();

            try
            {
                var (exito, mensaje, _) = await UnidadMedidaService.CrearAsync(
                    codigo, nombre, simbolo, _chkPermiteFraccion.Checked, sistema, SessionContext.Current?.UsuarioId);

                _lblEstado.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblEstado.Text = mensaje;

                if (exito)
                {
                    _txtCodigo.Clear();
                    _txtNombre.Clear();
                    _txtSimbolo.Clear();
                    _txtSistema.Clear();
                    _chkPermiteFraccion.Checked = true;
                    await CargarAsync();
                }
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.UnidadesMedida.NoSeGuardoPrefijo + ex.Message;
            }
        }

        private async void Grid_CellValueChanged(object? sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0 || e.RowIndex >= _unidades.Count) return;
            if (_grid.Columns[e.ColumnIndex].DataPropertyName != nameof(UnidadMedidaDto.Activo)) return;

            var unidad = _unidades[e.RowIndex];
            try
            {
                var (exito, mensaje) = await UnidadMedidaService.ActualizarAsync(
                    unidad.Id, unidad.Nombre, unidad.Simbolo, unidad.PermiteFraccion, unidad.Sistema, unidad.Activo,
                    SessionContext.Current?.UsuarioId);

                _lblEstado.ForeColor = exito ? UiTheme.Primario : UiTheme.Error;
                _lblEstado.Text = mensaje;
                if (!exito) await CargarAsync(); // revierte el checkbox si el SP rechazó el cambio (ej. la unidad "Unidad")
            }
            catch (Exception ex)
            {
                _lblEstado.ForeColor = UiTheme.Error;
                _lblEstado.Text = Textos.UnidadesMedida.NoSeGuardoPrefijo + ex.Message;
                await CargarAsync();
            }
        }
    }
}
