# -*- coding: utf-8 -*-
from odoo import models, fields, _


class MasterPlanApproval(models.Model):
    _name = 'hr.master.plan.approval'
    _description = 'Yearly Manpower Plan Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'master_plan_id'

    master_plan_id = fields.Many2one('hr.master.plan', string='Yearly Manpower Plan')
