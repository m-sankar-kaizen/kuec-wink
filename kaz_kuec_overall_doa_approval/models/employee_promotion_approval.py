# -*- coding: utf-8 -*-
from odoo import models, fields, _


class EmployeePromotionApproval(models.Model):
    _name = 'employee.promotion.approval'
    _description = 'Employee Promotion Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'employee_promotion_id'

    employee_promotion_id = fields.Many2one('employee.promotion', string='Employee Promotion')
