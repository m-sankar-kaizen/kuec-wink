# -*- coding: utf-8 -*-
from odoo import models, fields


class HrLoanLine(models.Model):
    """
    Model: hr.loan.line
    Purpose: Individual installment record for each loan/housing advance
    """
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    amount = fields.Float(string="Amount", required=True)
    paid = fields.Boolean(string="Paid")
    loan_id = fields.Many2one('hr.loan', string="Loan / Housing Advance Ref.")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.")
