# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BudgetTransferLine(models.TransientModel):
    """
    Transient model representing a single budget transfer line within the budget transfer wizard.

    Fields:
        increase_budget_id (Many2one): The budget line to which funds will be increased (credited).
        decrease_budget_id (Many2one): The budget line from which funds will be decreased (debited).
            The domain excludes budgets in 'cancel' state.
        amount (Float): The amount requested to transfer.
        wizard_id (Many2one): Reference to the parent budget transfer wizard.
        remaining_amount (Float, computed): The remaining available amount in the decrease budget line,
            calculated as the difference between planned and practical amounts.
    """

    _name = 'budget.transfer.line'
    _description = 'Budget transfer line'

    increase_budget_id = fields.Many2one(
        'budget.line',
        string="Increase Budget",
        required=True,
        help="Budget line to increase by the requested amount.")

    decrease_budget_id = fields.Many2one(
        'budget.line',
        string="Decrease Budget",
        help="Budget line to decrease. Cannot be in cancelled state.")

    amount = fields.Float(
        string="Requested Amount",
        help="Amount to transfer from the decrease budget to the increase budget.")

    wizard_id = fields.Many2one(
        comodel_name='budget.transfer.wizard',
        string='Wizard',
        help="Reference to the parent budget transfer wizard.")

    remaining_amount = fields.Float(
        string='Remaining Amount',
        compute='_compute_remaining',
        help="Computed remaining available amount in the decrease budget line.")

    @api.depends('decrease_budget_id')
    def _compute_remaining(self):
        """
        Compute the remaining amount available for transfer from the decrease budget line.

        Calculation:
            remaining_amount = |planned_amount| - |practical_amount|

        If no decrease_budget_id is set, remaining_amount is zero.
        """
        for line in self:
            if line.decrease_budget_id:
                line.remaining_amount = (
                        abs(line.decrease_budget_id.budget_amount) - abs(
                    line.decrease_budget_id.achieved_amount)
                )
            else:
                line.remaining_amount = 0
