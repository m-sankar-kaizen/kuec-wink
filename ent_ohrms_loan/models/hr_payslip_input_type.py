# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayslipInputType(models.Model):
    """Extends hr.payslip.input.
    type to associate an input type with a salary rule."""
    _inherit = 'hr.payslip.input.type'

    input_id = fields.Many2one('hr.salary.rule',
                               string="Linked Salary Rule",
                               help="The salary rule this input type belongs to.")
