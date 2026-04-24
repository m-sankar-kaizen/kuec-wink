from odoo import models, fields

class AccountAsset(models.Model):
    _inherit = "account.asset"

    company_code = fields.Selection(related='company_id.company_code',
                                    string="Company Code")