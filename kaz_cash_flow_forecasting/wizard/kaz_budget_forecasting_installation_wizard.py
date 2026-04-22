from odoo import fields, models, api, tools
import logging
from odoo.modules.module import get_module_resource
import base64

_logger = logging.getLogger(__name__)


class kazBudgetForecastingInstallationWizard(models.TransientModel):
    _name = 'kaz.budget.forecasting.installation.wizard'
    _description = 'kaz Budget Forecasting Installation Wizard'

    install_kaz_budget_forecasting = fields.Boolean(string="Enable Budget Forecasting")
    @api.model
    def default_get(self, fields):
        res = super(kazBudgetForecastingInstallationWizard, self).default_get(fields)
        install_kaz_budget_forecasting = self.env['kaz.budget.forecast.settings'].search([]).include_budget_forecast
        if install_kaz_budget_forecasting:
            res[
                'install_kaz_budget_forecasting'] = True if install_kaz_budget_forecasting == 'installed' else False
        return res

    def execute(self):
        install_kaz_budget_forecasting = self.env['kaz.budget.forecast.settings'].search([]).include_budget_forecast
        self.unzip_and_install_extended_module(True, install_kaz_budget_forecasting)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def unzip_and_install_extended_module(self, state, install_kaz_advance_reordering):
        try:
            kaz_budget_forecasting = self.env['ir.module.module'].sudo().search(
                [('name', '=', 'kaz_budget_forecasting')],
                limit=1)
            source_dir = __file__.replace('/wizard/kaz_budget_forecasting_installation_wizard.py',
                                          '/module/kaz_budget_forecasting.zip')
            target_dir = \
                __file__.split('/kaz_cash_flow_forecasting/wizard/kaz_budget_forecasting_installation_wizard.py')[0]
            if not state and kaz_budget_forecasting and kaz_budget_forecasting.state == 'installed':
                status = 'uninstall'
            if state:
                if kaz_budget_forecasting and kaz_budget_forecasting.state != 'installed':
                    status = 'install'
                elif not kaz_budget_forecasting:
                    import zipfile
                    with zipfile.ZipFile(source_dir, 'r') as zip_ref:
                        zip_ref.extractall(target_dir)
                    self.env['ir.module.module'].sudo().action_update_list_for_budget_forecasting()
            return True
        except Exception as e:
            _logger.info("====================%s==================" % e)
            return False
