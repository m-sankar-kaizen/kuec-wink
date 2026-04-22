from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountBudgetPost(models.Model):
    _inherit = 'account.budget.post'

    budgetary_position_tag_id = fields.Many2one(
        'account.account.tag')

    company_code = fields.Selection('Company Code',
                                    related='company_id.company_code',
                                    readonly=True)


    @api.constrains('budgetary_position_tag_id',
                    'account_ids',
                    'account_ids.tag_ids',
                    'account_ids.tag_ids.type'
                    )
    def check_budgetary_position_tag_id(self):
        for rec in self:
            if rec.company_code == 'KUEC':
                budgetary_position_tag_type = rec.budgetary_position_tag_id.type
                for account in rec.account_ids:
                    account_tag_types = account.tag_ids.mapped('type')
                    if budgetary_position_tag_type not in account_tag_types:
                        raise ValidationError(
                            _("At least one tag must be of type '%s' for each account.") % budgetary_position_tag_type)
