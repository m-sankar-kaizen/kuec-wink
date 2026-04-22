# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayslipInput(models.Model):
    """Extends hr.payslip.input to link an input line with a specific loan installment."""
    _inherit = 'hr.payslip.input'

    loan_line_id = fields.Many2one(
        'hr.loan.line',
        string="Loan / Housing Advance Installment",
        help="Link to the related loan installment line for tracking payment status."
    )
