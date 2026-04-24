from odoo import models, fields


class BudgetAnalytic(models.Model):
    _inherit = 'budget.analytic'

    short_code = fields.Char('Short Code')
