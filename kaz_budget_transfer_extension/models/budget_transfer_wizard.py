from odoo import models, fields


class BudgetTransferLine(models.TransientModel):
    _inherit = 'budget.transfer.line'

    increase_budget_tag_id = fields.Many2one(
        related='increase_budget_id.budget_line_tag_id')
    tag_type = fields.Selection(
        related='increase_budget_tag_id.type')
    decrease_budget_tag_id = fields.Many2one(
        related='decrease_budget_id.budget_line_tag_id')

