# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountBudgetPost(models.Model):
    _name = "account.budget.post"
    _order = "name"
    _description = "Budgetary Position"

    name = fields.Char('Name', required=True)
    account_ids = fields.Many2many('account.account', 'account_budget_rel',
                                   'budget_id', 'account_id', 'Accounts',
                                   domain=[('deprecated', '=', False)])
    company_id = fields.Many2one('res.company', 'Company',
                                 required=True,
                                 domain=lambda self: [
                                     ('id', 'in', self.env.companies.ids)],
                                 default=lambda self: self.env.company)

    def _check_account_ids(self, vals):
        if 'account_ids' in vals:
            account_ids = vals['account_ids']
        else:
            account_ids = self.account_ids
        if not account_ids:
            raise ValidationError(
                _('The budget must have at least one account.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_account_ids(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._check_account_ids(vals)
        return super().write(vals)
