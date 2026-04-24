from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CashForcastTag(models.Model):
    """Group of accounts used to seed a Forecast Type."""
    _name = "cash.forecast.tag"
    def _set_account_company(self):
        return self._context.get('company_id', False) or self.env.company.id
    name = fields.Char("Name")
    company_id = fields.Many2one('res.company', string='Company', default=_set_account_company)
    account_ids = fields.One2many('account.account', 'cash_forecast_tag', string='Accounts')
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            name=_("%s (copy)") % (self.name or ''))
        return super(CashForcastTag, self).copy(default)
    @api.constrains('name', 'company_id')
    def _check_forecast_tag(self):
        duplicate_records = self.search([('id', '!=', self.id),
                                         ('name', '=', self.name),
                                         ('company_id', '=', self.company_id.id)])
        if duplicate_records:
            raise ValidationError(_('Forecast Category you want to create is duplicate'))