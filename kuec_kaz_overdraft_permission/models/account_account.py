from odoo import models, fields

class AccountAccount(models.Model):
    _inherit = 'account.account'

    credit_limit_control = fields.Boolean()
    allowed_limit = fields.Float()
