using System;
using System.ComponentModel;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;
using Sistemas.Core.Inventory;
using Sistemas.Core.Inventory.Models;
using Sistemas.Core.Security;
using Sistemas.Core.UI.Common;

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

            var pnlTop = new Panel { Dock = DockStyle.Top, Height = 96, BackColor = Color.White };

            var lblCodigo = new Label { Text = Textos.UnidadesMedida.CampoCodigo, AutoSize = true, Location = new Point(16, 8) };
            _txtCodigo = new TextBox { Location = new Point(16, 28), Size = new Size(80, 26), MaxLength = 10 };

            var lblNombre = new Label { Text = Textos.UnidadesMedida.CampoNombre, AutoSize = true, Location = new Point(106, 8) };
            _txtNombre = new TextBox { Location = new Point(106, 28), Size = new Size(180, 26), MaxLength = 50 };

            var lblSimbolo = new Label { Text = Textos.UnidadesMedida.CampoSimbolo, AutoSize = true, Location = new Point(296, 8) };
            _txtSimbolo = new TextBox { Location = new Point(296, 28), Size = new Size(70, 26), MaxLength = 10 };

            var lblSistema = new Label { Text = Textos.UnidadesMedida.CampoSistema, AutoSize = true, Location = new Point(376, 8) };
            _txtSistema = new TextBox { Location = new Point(376, 28), Size = new Size(110, 26), MaxLength = 20 };

            _chkPermiteFraccion = new CheckBox { Text = Textos.UnidadesMedida.CampoPermiteFraccion, AutoSize = true, Location = new Point(496, 32), Checked = true };

            var btnAgregar = new Button { Text = Textos.UnidadesMedida.BotonAgregar, Location = new Point(16, 60), Size = new Size(110, 28), BackColor = UiTheme.Primario, ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
            btnAgregar.FlatAppearance.BorderSize = 0;
            btnAgregar.Click += BtnAgregar_Click;

            _lblEstado = new Label { ForeColor = UiTheme.Error, AutoSize = false, Size = new Size(500, 24), Location = new Point(136, 64) };

            pnlTop.Controls.AddRange(new Control[]
            {
                lblCodigo, _txtCodigo, lblNombre, _txtNombre, lblSimbolo, _txtSimbolo,
                lblSistema, _txtSistema, _chkPermiteFraccion, btnAgregar, _lblEstado
            });

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
