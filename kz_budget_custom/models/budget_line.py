# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetLine(models.Model):
    """
    Extends the `crossovered.budget.lines` v16 --> `budget.line` v18 model
     with masked (absolute-value) computed fields
    for user-friendly display and added logic for:

    - Expense/income direction control
    - Auto-filling analytic account from budget's department
    - Accurate practical and theoretical computations
    """
    _inherit = "budget.line"

    masked_planned_amount = fields.Monetary(
        string='Planned Amount',
        required=True,
        help="User-visible amount. Negative sign"
             " will be applied for expenses internally."
    )
    # masked_practical_amount = fields.Monetary(
    #     string='Practical Amount',
    #     compute='_compute_practical_amount',
    #     help="Displayed as absolute value of practical amount."
    # )
    masked_theoritical_amount = fields.Monetary(
        string='Theoretical Amount',
        compute='_compute_masked_theoritical_amount',
        help="Displayed as absolute value of theoretical amount."
    )

    expense = fields.Boolean(
        string='Expense',
        default=True,
        help="If checked, the planned amount "
             "will be stored as negative internally."
    )

    change_count = fields.Boolean(
        string='Internal change flag',
        help="Used to avoid resetting analytic"
             " account on repeated onchange triggers."
    )
    general_budget_id = fields.Many2one('account.budget.post')

    achieved_amount = fields.Monetary(
        string="Achieved Amount",
        compute="_compute_achieved_amount"
    )
    achieved_percentage = fields.Float(
        compute='_compute_achieved_amount',
        string='Achieved (%)')

    def _compute_achieved_amount(self):
        fnames = self._get_plan_fnames()

        for rec in self:
            rec.achieved_amount = 0
            rec.achieved_percentage = 0
            analytic = any(rec[fname] for fname in fnames)
            if rec.general_budget_id and not analytic:
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(debit - credit), 0)
                    FROM account_move_line
                    WHERE date >= %s
                      AND date <= %s
                      AND account_id = ANY(%s)
                      AND company_id = %s
                      AND move_id IN (SELECT id FROM account_move WHERE state='posted')
                """, (
                    rec.date_from,
                    rec.date_to,
                    rec.general_budget_id.account_ids.ids,
                    rec.company_id.id
                ))
                result = self.env.cr.fetchone()
                achieved = result[0] if result else 0
                rec.achieved_amount = -achieved if not rec.expense else achieved
            else:
                achieved = self.get_achieved_analytic_budgetary(rec)
                rec.achieved_amount = achieved if not rec.expense else -achieved

            if rec.achieved_amount:
                percentage = rec.budget_amount and (
                        rec.achieved_amount / rec.budget_amount)
                rec.achieved_percentage = percentage if not rec.expense else -percentage

    def get_achieved_analytic_budgetary(self, line):
        """
        Compute achieved amount for a budget line considering:
        - multiple plan fields (account_id, x_plan2, ...)
        - auto_account_id is computed, so we filter using ORM
        - optional general_budget_id filter via account_budget_rel
        """
        fnames = self._get_plan_fnames()
        analytic_accounts = [line[fname].id for fname in fnames if line[fname]]

        if not analytic_accounts:
            return 0.0

        domain = [('auto_account_id', 'in', analytic_accounts), ('date', '>=', line.date_from),
                  ('date', '<=', line.date_to)]
        if line.general_budget_id:
            general_accounts = line.general_budget_id.account_ids.ids
            domain.append(('general_account_id', 'in', general_accounts))

        # Use read_group to perform the SUM in SQL, preventing a MemoryError.
        achieved_data = self.env['account.analytic.line'].read_group(
            domain=domain,
            fields=['amount:sum'],
            groupby=[]
        )
        return achieved_data[0]['amount'] if achieved_data and achieved_data[0]['amount'] else 0.0

    @api.constrains(lambda self: self._get_plan_fnames() + ['general_budget_id'])
    def _check_account_id(self):
        """
        Ensure that at least one analytic account or a general budget is set.
        """
        fnames = self._get_plan_fnames()
        for line in self:
            # Check if at least one analytic field or general_budget_id is filled
            if not any(line[fname] for fname in fnames) and not line.general_budget_id:
                raise ValidationError(
                    _("At least one analytic account or general budget must be set."))

    @api.onchange('general_budget_id')
    def _onchange_general_budget(self):
        """
        When general budget is selected, auto-fill analytic account
        from the parent budget's department.
        """
        if not self.change_count:
            if self.budget_analytic_id and self.budget_analytic_id.dep_analytic_account_id:
                self.auto_account_id = self.budget_analytic_id.dep_analytic_account_id.id
            self.change_count = True

    @api.onchange('masked_planned_amount')
    def _onchange_masked_planned_amount(self):
        """
        Store planned amount with appropriate sign based on
        whether the line is expense or income.
        """
        if self.masked_planned_amount:
            self.budget_amount = -self.masked_planned_amount if self.expense else self.masked_planned_amount

    # def _compute_practical_amount(self):
    #     for line in self:
    #         line.masked_practical_amount = 0

    @api.depends('date_from', 'date_to')
    def _compute_masked_theoritical_amount(self):
        """
        Calculates theoretical (elapsed) amount for each line
        based on how much of the duration has passed as of today.
        """
        today = fields.Date.context_today(self)
        for line in self:
            if not line.date_from or not line.date_to:
                line.theoritical_amount = 0
                line.theoritical_percentage = 0
                # keep masked amount in sync if you still need it
                if hasattr(line, "masked_theoritical_amount"):
                    line.masked_theoritical_amount = 0
                continue

            # total duration (inclusive of start/end)
            total_days = (line.date_to - line.date_from + timedelta(days=1)).days
            # elapsed duration as of today (inclusive)
            elapsed_days = (today - line.date_from + timedelta(days=1)).days

            if elapsed_days < 0:
                # Budget not started yet
                theo_amt = 0.0
            elif today < line.date_to and total_days > 0:
                # Budget in progress
                theo_amt = (elapsed_days / total_days) * line.budget_amount
            else:
                # Budget finished or today beyond date_to
                theo_amt = line.budget_amount

            line.theoritical_amount = theo_amt
            line.theoritical_percentage = (
                (theo_amt / line.budget_amount) if line.budget_amount else 0
            )
            line.masked_theoritical_amount = abs(theo_amt)
