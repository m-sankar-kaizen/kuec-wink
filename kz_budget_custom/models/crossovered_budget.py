# -*- coding: utf-8 -*-
from odoo import models, fields


class CrossoveredBudget(models.Model):
    # Deprecated
    _name = "crossovered.budget"
    _description = "Budget"

    company_id = fields.Many2one('res.company', string="Company", required=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help="Currency of the company for reporting totals."
    )
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'crossovered_budget_id',
                                              'Budget Lines', )
