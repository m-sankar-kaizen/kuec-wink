# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BudgetAnalytic(models.Model):
    """
    Inherits the core `crossovered.budget` v16 --> `budget.analytic`
    in v18 model to extend budgeting features with:

    - Department-based budgeting (`department_id`)
    - Automatically linked analytic account from department
    - Computed totals for planned, practical, and theoretical amounts
    - Currency field for monetary computation context
    """
    _inherit = "budget.analytic"

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        readonly=True,
        help="Currency of the company for reporting totals."
    )

    total_planned_amount = fields.Monetary(
        compute='_compute_total_planned_amount',
        string="Total Planned Amount",
        help="Sum of all planned amounts for the budget lines (absolute values)."
    )
    total_practical_amount = fields.Monetary(
        compute='_compute_total_practical_amount',
        string="Total Practical Amount",
        help="Sum of all practical (actual) amounts from budget lines (absolute values)."
    )
    total_theoritical_amount = fields.Monetary(
        compute='_compute_total_theoritical_amount',
        string="Total Theoretical Amount",
        help="Sum of all theoretical (elapsed proportion) values for budget lines (absolute values)."
    )

    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Department',
        help="Used to link budgets to departments."
    )

    dep_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Department Analytic Account',
        related='department_id.analytic_account_id',
        help="Auto-filled analytic account based on the selected department."
    )

    @api.depends('budget_line_ids.budget_amount',
                 'budget_line_ids')
    def _compute_total_planned_amount(self):
        """
        Compute total planned amount by summing absolute values of planned_amounts
        across all budget lines.
        """
        for budget in self:
            budget.total_planned_amount = abs(
                sum(budget.budget_line_ids.mapped('budget_amount')))

    @api.depends('budget_line_ids.achieved_amount',
                 'budget_line_ids')
    def _compute_total_practical_amount(self):
        """
        Compute total actual (practical) amount by summing absolute values
        from all budget lines.
        """
        for budget in self:
            budget.total_practical_amount = abs(
                sum(budget.budget_line_ids.mapped('achieved_amount')))

    @api.depends('budget_line_ids.theoritical_amount',
                 'budget_line_ids')
    def _compute_total_theoritical_amount(self):
        """
        Compute total theoretical (elapsed time) value from all budget lines.
        """
        for budget in self:
            budget.total_theoritical_amount = abs(
                sum(budget.budget_line_ids.mapped('theoritical_amount')))
