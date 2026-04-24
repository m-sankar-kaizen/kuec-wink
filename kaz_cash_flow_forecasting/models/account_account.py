from odoo import fields, models, api, _
from odoo.addons.sale_stock.models.res_company import company
class AccountAccount(models.Model):
    """Extend chart of accounts to map accounts to a Cash Forecast Tag,
        and provide an action to (batch) create/update Forecast Types from selected accounts/tags."""
    _inherit = 'account.account'
    _description = 'Chart Of Account'
    cash_forecast_tag = fields.Many2one("cash.forecast.tag", string="Cash Forecast Tag", company_dependent=True)
    def create_forecast_type(self):
        """Action: from selected accounts, (re)build kaz.cash.forecast.type records.
        Priority:
         - If accounts have a Forecast Tag: one type per tag with its tag-bound accounts.
         - Otherwise: one type per account.
        """
        forecasting_type = self.env['kaz.cash.forecast.type']
        account = self._context.get('active_ids')
        company_ids = self.env['res.company'].browse(self._context.get('allowed_company_ids'))
        for company_id in company_ids:
            account_ids = self.with_company(company_id).browse(account)
            forecasting_tags = account_ids.mapped('cash_forecast_tag')
            account_without_tag = account_ids.filtered(lambda a: not a.cash_forecast_tag)
            for tag in forecasting_tags:
                vals = {'name': tag.name,
                        'account_ids': [(6, 0, tag.account_ids.ids)],
                        'company_id': tag.company_id.id,
                        'forecasting_tag': tag.id}

                forecasting_type = forecasting_type.search([('forecasting_tag', '=', tag.id),
                                                            ('company_id', '=', tag.company_id.id)])
                if forecasting_type:
                    forecasting_type.update(vals)
                else:
                    forecasting_type.create(vals)
        for account in account_without_tag:
            for company_id in account.company_ids:
                vals = {'name': account.name,
                        'account_ids': [(6, 0, account.ids)],
                        'company_id': company_id.id,
                        }
                forecasting_type = forecasting_type.search([('name', '=', account.name),
                                                            ('company_id', '=', company_id.id)])
                if forecasting_type:
                    forecasting_type.update(vals)
                else:
                    forecasting_type.create(vals)
        return {
            'name': _('Cash Forecast Type'),
            'view_mode': 'list,form',
            'res_model': 'kaz.cash.forecast.type',
            'type': 'ir.actions.act_window',
        }