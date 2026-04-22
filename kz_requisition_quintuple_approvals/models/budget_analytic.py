# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


# enterprise/account_budget/models/budget_analytic.py

class BudgetAnalytic(models.Model):
    """
    Extension of the crossovered.budget model to compute and track:
    - total_reserved_amount: Aggregated reserved amounts from all related budget lines.
    - total_committed_amount: Aggregated committed amounts from all related budget lines.
    """
    _inherit = "budget.analytic"

    total_reserved_amount = fields.Monetary(
        string="Reserved Amount",
        compute="_compute_total_reserved_amount",
        help="Sum of all reserved amounts from the budget lines."
    )

    total_committed_amount = fields.Monetary(
        string="Committed Amount",
        compute="_compute_total_committed_amount",
        help="Sum of all committed amounts from the budget lines."
    )

    @api.depends('budget_line_ids.reserved_amount', 'budget_line_ids')
    def _compute_total_reserved_amount(self):
        """
        Computes total reserved amount by summing reserved_amount of all budget lines.
        """
        for rec in self:
            rec.total_reserved_amount = sum(rec.budget_line_ids.mapped('reserved_amount'))

    @api.depends('budget_line_ids.committed_amount', 'budget_line_ids')
    def _compute_total_committed_amount(self):
        """
        Computes total committed amount by summing committed_amount of all budget lines.
        """
        for rec in self:
            rec.total_committed_amount = sum(rec.budget_line_ids.mapped('committed_amount'))

    def action_login_external_db(self):
        """
        Placeholder method for potential external database login or integration logic.
        Currently unimplemented.
        """
        pass
