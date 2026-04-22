from odoo import models, fields


class AccountTag(models.Model):
    _inherit = 'account.account.tag'

    type = fields.Selection([
        ('general', "General"),
        ('opex', "OpEx"),
        ('capex', "CapEx"),
    ],
        default='general',
        required=True)
