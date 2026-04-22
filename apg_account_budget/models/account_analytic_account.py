# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    budget_line = fields.One2many('budget.lines',
                                  'analytic_account_id',
                                  'Budget Lines')

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        return res
