# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BudgetTransferLine(models.Model):
    """
    A single line within a budget transfer request. Indicates a reallocation of
    amount from a source budget (decrease) to a destination budget (increase).
    """
    _name = 'budget.transfer.request.line'
    _description = 'Budget Transfer Request Line'

    increase_budget_id = fields.Many2one(
        'budget.line',
        string="Increase Budget",
        help="The budget line to which the amount will be added."
    )

    decrease_budget_id = fields.Many2one(
        'budget.line',
        string="Decrease Budget",
        domain=[('budget_analytic_state', '!=', 'canceled')],
        help="The budget line from which the amount will be deducted."
    )

    amount = fields.Float(
        string="Requested Amount",
        help="Amount to transfer from decrease to increase budget."
    )

    remaining_amount = fields.Float(
        string='Remaining Amount',
        compute='_compute_remaining',
        help="Computed available amount left in the decrease budget line."
    )

    budget_transfer_request_id = fields.Many2one(
        comodel_name='budget.transfer.request',
        string='Budget Transfer Request',
        help="Parent budget transfer request record."
    )

    @api.depends('decrease_budget_id')
    def _compute_remaining(self):
        """
            Compute method for the `remaining_amount` field.

            Calculates the remaining budget available in the `decrease_budget_id` budget line
            by subtracting the practical (used) amount from the planned (total allocated) amount.

            This value represents how much of the budget line is still available for transfer.

            Logic:
            - If a decrease budget line is selected:
                remaining = |planned_amount| - |practical_amount|
            - If no decrease budget line is selected:
                remaining = 0
            """
        for line in self:
            if line.decrease_budget_id:
                line.remaining_amount = (abs(line.decrease_budget_id.budget_amount) - abs(
                    line.decrease_budget_id.achieved_amount))

            else:
                line.remaining_amount = 0
