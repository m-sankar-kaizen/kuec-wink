from odoo import api, fields, models, _
from odoo.exceptions import UserError
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    include_budget_forecast = fields.Boolean("Include Budget Forecast", help="Set True To Include Budget Forecast",
                                             config_parameter='kaz_cash_flow_forecasting.include_budget_forecast')
    module_kaz_budget_forecasting = fields.Boolean(string="Install kaz Budget Forecasting")

    def action_open_budget_forecast_wizard(self):
        if self.env['ir.module.module'].sudo().search(
                [('name', '=', 'web_enterprise')]).state == 'installed':
            action_values = self.sudo().sudo().env.ref(
                'kaz_cash_flow_forecasting.actions_kaz_budget_forecasting_installation_wizard').sudo().read()[0]
        else:
            raise UserError(_("You don't have Enterprise Version of odoo please upgrade to enable budget forecast"))
        return action_values