# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """
    Extends res.company to store default banking information for payroll purposes.

    Fields:
        - bank_id: Bank used for salary transfer.
        - account_no: Account number from which salaries are paid.
    """
    _inherit = 'res.company'

    bank_id = fields.Many2one(
        comodel_name='res.bank',
        string='Bank Name',
        required=False,
        help="Bank to be used for paying employees' salaries."
    )

    account_no = fields.Char(
        string='Account No',
        required=False,
        help="Default company account number for employee salary transfers."
    )
