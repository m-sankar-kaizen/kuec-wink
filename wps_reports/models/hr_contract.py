# -*- coding: utf-8 -*-
from odoo import models, fields


class HrContract(models.Model):
    """
    Extension of the hr.contract model to include additional fields relevant to
    employee classification, loan tracking, and hiring metadata.

    Fields:
        person_extra_info (Char): External or internal reference for personal info.
        assignment_category_id (Many2one): Links to a custom assignment category.
        reference (Char): Reference number for external/contractual tracking.
        loan_amount (Monetary): Amount of loan granted under the contract.
        installment (Integer): Number of installments to repay the loan.
        creation_date (Date): Date on which the contract record was created.
        ku_hire_date (Date): Specific hiring date at the institution (e.g., university hire date).
    """
    _inherit = 'hr.contract'

    person_extra_info = fields.Char(
        string="Person Extra Info ID",
        help="Reference to external or internal personal info system."
    )

    assignment_category_id = fields.Many2one(
        'hr.assignment.category',
        string="Assignment Category",
        help="Category used to classify the assignment type (e.g., academic, administrative)."
    )

    reference = fields.Char(
        string="Reference #",
        help="External or internal reference number for the contract."
    )

    loan_amount = fields.Monetary(
        string="Loan Amount",
        currency_field='currency_id',
        help="Total loan amount granted as part of the contract."
    )

    installment = fields.Integer(
        string="Installment",
        help="Number of monthly installments to repay the loan."
    )

    creation_date = fields.Date(
        string="Creation Date",
        readonly=True,
        default=fields.Date.today,
        help="Date when the contract was created."
    )

    ku_hire_date = fields.Date(
        string='Ku Hire Date',
        help="Specific hire date at Kuwait University or similar institution."
    )

    other_allowances = fields.Float(
        string='Other Allowances',
        required=False,
        help="Additional financial allowance"
             " paid to the employee that's not covered by standard rules."
    )