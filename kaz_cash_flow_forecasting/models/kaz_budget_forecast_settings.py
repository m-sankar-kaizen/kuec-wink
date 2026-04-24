from odoo import models, fields, api, _
from odoo.exceptions import UserError
class KazBudgetForecastSettings(models.Model):
    """Settings façade for enabling budget forecasting and opening the installer wizard."""
    _name = 'kaz.budget.forecast.settings'
    _description = """
        This model is used to install and automate some activities in the budget forecasting
        Like, Auto confirm, validate and done Budget... 
    """
    name = fields.Char(string="Cash Forecast", default="Cash Forecast")
    include_budget_forecast = fields.Boolean(string="Include Budget Forecast",
                                             help="Set True To Include Budget Forecast", compute="_compute_extract_budget_forecast")
    module_kaz_budget_forecasting = fields.Boolean(string="Install kaz Budget Forecasting"
                                                    , compute="_compute_install_uninstall_budget_forecast")
    def action_open_budget_forecast_wizard(self):
        """Open the budget forecasting extraction/installer wizard (Enterprise check)."""
        if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'web_enterprise')]).state == 'installed':
            action_values = self.sudo().sudo().env.ref(
                'kaz_cash_flow_forecasting.actions_kaz_budget_forecasting_installation_wizard').sudo().read()[0]
        else:
            raise UserError(_("You don't have Enterprise Version of odoo please upgrade to enable budget forecast"))
        return action_values
    def action_install_budget_forecast(self):
        """Install kaz_budget_forecasting module if available."""
        kaz_budget_forecasting_module = self.env['ir.module.module'].search([
            ('name', '=', 'kaz_budget_forecasting'), ('state', '!=', 'installed')])
        if kaz_budget_forecasting_module:
            kaz_budget_forecasting_module.button_immediate_install()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    @api.model
    def open_record_action(self):
        """Return a direct action to the single settings record (id=1 fallback)."""
        view_id = self.env.ref('kaz_cash_flow_forecasting.kaz_budget_forecast_settings_form').id
        record = self.env['kaz.budget.forecast.settings'].search([('id','=',1)]).id
        return {'type': 'ir.actions.act_window',
                'name': _('Settings - Budget Forecast'),
                'res_model': 'kaz.budget.forecast.settings',
                'target': 'current',
                'res_id': record,
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }
    def _compute_install_uninstall_budget_forecast(self):
        for record in self:
            kaz_budget_forecasting_module = self.env['ir.module.module'].search([
                ('name', '=', 'kaz_budget_forecasting')])
            if kaz_budget_forecasting_module.state != 'installed':
                record.module_kaz_budget_forecasting = False
            else:
                record.module_kaz_budget_forecasting = True
    def _compute_extract_budget_forecast(self):
        for record in self:
            kaz_budget_forecasting = self.env['ir.module.module'].search(
                [('name', '=', 'kaz_budget_forecasting')])
            if not kaz_budget_forecasting:
                record.include_budget_forecast = False
            else:
                record.include_budget_forecast = True