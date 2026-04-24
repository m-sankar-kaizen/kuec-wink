# -*- coding: utf-8 -*-
from odoo import models

class HrLoanLine(models.Model):
    """
    Extension of `hr.loan.line` to add logic for marking an installment as paid.

    Methods:
        - `action_paid_amount`: To be overridden to mark the loan line as paid
          when included in a payslip. Currently a stub.
    """
    _inherit = "hr.loan.line"

    def action_paid_amount(self, month):
        """
        Stub for handling loan installment payment tracking.

        Args:
            month (str): Month name in 'MMMM-y' format, e.g., 'July-2025'.

        This should be overridden to set flags like `paid=True`, or record actual payment info.
        """
        pass
