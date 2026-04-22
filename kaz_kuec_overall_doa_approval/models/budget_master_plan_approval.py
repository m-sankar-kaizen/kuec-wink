# -*- coding: utf-8 -*-
from odoo import models, fields, _


class BudgetMasterPlanApproval(models.Model):
    _name = 'budget.master.plan.approval'
    _description = 'Budget Master Plan Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'master_plan_id'

    master_plan_id = fields.Many2one('budget.master.plan', string='Budget Master Plan')
