# -*- coding: utf-8 -*-
import babel

from datetime import datetime, time

from odoo import models, fields, tools, _


class HrPayslip(models.Model):
    """
    Extension of `hr.payslip` to integrate loan repayment tracking.

    Enhances `action_payslip_done` to notify the `hr.loan.line` model that
    an installment has been paid.

    Methods:
        - `action_payslip_done`: Informs loan line(s) that the related amount has been paid
          for the given month when payslip is validated.
    """
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        """
        Finalize the payslip and notify any associated loan line(s)
        that the current month's installment has been paid.

        Calls `loan_line_id.action_paid_amount(month)` for each input line with a loan line.

        Returns:
            Result of the super call to `action_payslip_done()`.
        """
        for payslip in self:
            for line in payslip.input_line_ids:
                # Extract payslip period start
                date_from = payslip.date_from

                # Convert to datetime (00:00 hrs of date_from)
                tym = datetime.combine(fields.Date.from_string(date_from), time.min)

                # Get locale for formatting month-year
                locale = self.env.context.get('lang') or 'en_US'
                month = tools.ustr(
                    babel.dates.format_date(date=tym, format='MMMM-y', locale=locale))

                # If input line is linked to loan line, notify that line
                if line.loan_line_id:
                    line.loan_line_id.action_paid_amount(month)

        # Call super to finalize payslip
        return super().action_payslip_done()
