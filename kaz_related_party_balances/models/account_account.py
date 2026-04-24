from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_related_party = fields.Boolean(string="Related Party")
    related_company_id = fields.Many2one('res.company')


