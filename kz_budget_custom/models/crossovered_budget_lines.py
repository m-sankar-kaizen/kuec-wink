# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrossoveredBudgetLines(models.Model):
    # Deprecated
    _name = "crossovered.budget.lines"
    _description = "Budget Line"

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    crossovered_budget_id = fields.Many2one('crossovered.budget', 'Budget', ondelete='cascade', index=True, required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help="Currency of the company for reporting totals."
    )
    reserved_amount = fields.Monetary(
        string="Reserved Amount",
        compute="_compute_reserved_amount",
        help="Total amount reserved for purchases in 'draft' or 'sent' states."
    )

    committed_amount = fields.Monetary(
        string="Committed Amount",
        compute="_compute_committed_amount",
        help="Total committed amount for purchases confirmed or completed, but not invoiced."
    )

    @api.depends('analytic_account_id')
    def _compute_reserved_amount(self):
        """
        Computes the reserved amount for the budget line.
        Reserved amount is calculated for requisitions in states other than
        'draft', 'rejected', or 'cancel', where the related purchases are still in 'draft' or 'sent'.
        """
        for line in self:
            line.reserved_amount = 0

    @api.depends('analytic_account_id')
    def _compute_committed_amount(self):
        """
        Computes the committed amount for the budget line.
        Committed amount is calculated for requisitions in 'completed' state
        where related purchases are in 'purchase' or 'done' state but not yet invoiced.
        """
        for line in self:
            line.committed_amount = 0

