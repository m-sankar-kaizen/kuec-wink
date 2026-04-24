# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    """
    Inherit: hr.employee
    Add computed field for housing advance count
    """
    _inherit = "hr.employee"

    loan_count = fields.Integer(string="Loan / Housing Advance Count",
                                compute='_compute_employee_loans')

    def _compute_employee_loans(self):
        """Compute loan count for dashboard or smart buttons"""
        self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])


