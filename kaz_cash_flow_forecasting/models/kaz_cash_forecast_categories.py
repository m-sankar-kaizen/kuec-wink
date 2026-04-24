from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import json
class KazCashForecastCategory(models.Model):
    """Top-level forecast grouping (Cash-In, Cash-Out, Opening, Net, Closing)."""
    _name = 'kaz.cash.forecast.categories'
    _description = "Cash Forecast Category"
    _order = 'sequence'
    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    is_group_for_opening = fields.Boolean("Is Group For Opening Balance", default=False)
    type = fields.Selection([('income', 'Cash In'), ('expense', 'Cash Out'),
                             ('opening', 'Opening Forecast'), ('net_forecast', 'Net Forecasting'),
                             ('closing', 'Closing Forecast'), ('pending', 'Pending')],
                            string="Group")
    kanban_dashboard_graph = fields.Text(compute='_compute_kanban_dashboard_graph')
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            name=_("%s (copy)") % (self.name or ''))
        return super(KazCashForecastCategory, self).copy(default)
    def _compute_kanban_dashboard_graph(self):
        """Prepare Kanban bar data (forecast values by type)."""
        for data in self:
            data.kanban_dashboard_graph = json.dumps(data.get_bar_graph_datas())
    def get_bar_graph_datas(self):
        types = self.env['kaz.cash.forecast.type'].search([('cash_forecast_category_id.id', '=', self.id)])
        list_data = []
        for type_record in types:
            data = {}
            data_case = self.env['kaz.cash.forecast'].search([('forecast_type_id', '=', type_record.id)])
            if data_case:
                data['label'] = type_record.name
                data['value'] = sum(data_case.mapped('forecast_value'))
                data['type'] = 'future'
                list_data.append(data)
        result_data = list_data
        if result_data.__len__():
            return [{'values': result_data, 'title': "graph_title"}]
        else:
            return [{'values': [{'label': 'No Data Found', 'value': 0, 'type': ''}], 'title': "dummy"}]
    def open_action(self):
        """Open form for this category (used by Kanban title)."""
        return {
            'name': _('Refund Orders'),
            'view_mode': 'form',
            'res_model': 'kaz.cash.forecast.categories',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
        }
    @api.constrains('name')
    def _check_forecast_categories(self):
        duplicate_records = self.search([('id', '!=', self.id),
                                         ('name', '=', self.name)])
        if duplicate_records:
            raise ValidationError(_('Forecast Category you want to create is duplicate'))
    def document_layout_save(self):
        return self.env['onboarding.onboarding.step'].action_validate_step(
            'kaz_cash_flow_forecasting.onboarding_onboarding_step_forecast_categories')