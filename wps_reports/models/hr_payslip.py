# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayslip(models.Model):
    """
    Extension of the hr.payslip model to include a payment date field.

    Fields:
        payment_date (Date): Actual payment date for the payslip, defaulting to today.
    """
    _inherit = 'hr.payslip'

    payment_date = fields.Date(
        string='Payment Date',
        readonly=True,
        default=fields.Date.today,
        help="Date on which the salary was or will be paid."
    )
