from odoo import models, fields


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    tag_type = fields.Selection(
        related='budget_line_tag_id.type')
