from odoo import models, fields


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    short_code = fields.Char('Short Code')
