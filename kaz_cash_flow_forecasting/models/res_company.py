from odoo import fields, models, api, _

ONBOARDING_STEP_STATES = [
    ('not_done', "Not done"),
    ('just_done', "Just done"),
    ('done', "Done"),
]
DASHBOARD_ONBOARDING_STATES = ONBOARDING_STEP_STATES + [('closed', 'Closed')]


class ResCompany(models.Model):
    _inherit = "res.company"

    cash_dashboard_onboarding_state = fields.Selection(DASHBOARD_ONBOARDING_STATES,
                                                       string="State of the Cash dashboard onboarding panel",
                                                       default='not_done')

    fiscal_year_setup_data_state = fields.Selection(ONBOARDING_STEP_STATES,
                                                    string="State of the onboarding Fiscal Year data step",
                                                    default='not_done')

    forecast_category_setup_data_state = fields.Selection(ONBOARDING_STEP_STATES,
                                                          string="State of the onboarding Forecast Category data step",
                                                          default='not_done')
    forecast_type_setup_data_state = fields.Selection(ONBOARDING_STEP_STATES,
                                                      string="State of the onboarding Forecast Type data step",
                                                      default='not_done')
    create_forecast_data_state = fields.Selection(ONBOARDING_STEP_STATES,
                                                  string="State of the onboarding Create Forecast data step",
                                                  default='not_done'
                                                  )
    @api.model
    def action_close_cash_forecasting_onboarding(self):
        self.env.company.cash_dashboard_onboarding_state = 'closed'

    @api.model
    def cash_setting_init_fiscal_year_action(self):
        view_id = self.env.ref('kaz_cash_flow_forecasting.form_cash_forecast_fiscal_year').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Accounting Periods'),
            'view_mode': 'form',
            'res_model': 'cash.forecast.fiscal.year',
            'target': 'new',
            'views': [[view_id, 'form']],
        }

    @api.model
    def cash_setting_init_forecast_categories_action(self):
        view_id = self.env.ref('kaz_cash_flow_forecasting.form_kaz_cash_forecast_categories').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Forecast Categories'),
                'res_model': 'kaz.cash.forecast.categories',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }

    @api.model
    def cash_setting_init_forecast_type_action(self):
        view_id = self.env.ref('kaz_cash_flow_forecasting.form_kaz_cash_forecast_type').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Forecast Type'),
                'res_model': 'kaz.cash.forecast.type',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }
    
    @api.model
    def cash_setting_init_create_forecast_action(self):
        view_id = self.env.ref('kaz_cash_flow_forecasting.form_create_update_cash_forecast').id
        return {'type': 'ir.actions.act_window',
                'name': _('Create a Cash Forecast'),
                'res_model': 'create.update.cash.forecast',
                'target': 'new',
                'view_mode': 'form',
                'views': [[view_id, 'form']],
                }