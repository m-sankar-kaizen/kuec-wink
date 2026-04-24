# -*- coding: utf-8 -*-
from odoo import models, fields, _


class BudgetAnalytic(models.Model):
    _inherit = 'budget.analytic'

    is_readonly = fields.Boolean(default=False)

    def action_lock(self):
        self.ensure_one()
        self.is_readonly = True

    def action_unlock(self):
        self.ensure_one()
        self.is_readonly = False
