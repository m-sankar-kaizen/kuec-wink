# -*- coding: utf-8 -*-
from odoo import models


class HrPayslip(models.Model):
    """
    Extension of hr.payslip to handle housing advance logic.

    This model adds logic to:
    - Calculate and populate housing advance granted and deducted during the payslip period
    - Mark related loan lines as paid when the payslip is finalized
    - Update the loan as granted if applicable

    Key fields that should exist (likely added via custom inheritance):
    - `housing_advance_grant`: Total granted amount (not yet disbursed)
    - `housing_advance_deduction`: Total deduction amount (scheduled repayments)
    """
    _inherit = 'hr.payslip'

    def _calc_housing_advance(self):
        """
        Compute housing advance amounts for the payslip:
        - Sum loan amounts not yet marked as granted
        - Calculate installment deductions for the current period
        - Mark installments as paid if payslip is finalized (state == done)
        - Mark the loan as granted if it contains allowance lines (HOADALW)
        """
        for ps in self:
            if ps.employee_id:
                # Fetch approved housing loans for the employee
                housing_adv = self.env['hr.loan'].search([
                    ('employee_id', '=', ps.employee_id.id),
                    ('state', '=', 'approve')
                ])

                # Set total loan amount for ungranted loans
                ps.housing_advance_grant = sum(
                    housing_adv.filtered(lambda h: not h.loan_granted).mapped('loan_amount')
                ) if housing_adv else 0

                # Initialize deduction total
                total_deduction = 0
                # Filter granted loans
                granted_loans = housing_adv.filtered(lambda x: x.loan_granted)
                # Check if deduction line exists in payslip (based on salary rule code)
                has_deduction_line = bool(ps.line_ids.filtered(lambda x: x.code in ['HOADLWD']))

                # Iterate through granted loans
                for loan in granted_loans:
                    # Get installment lines falling within the payslip period
                    filtered_lines = loan.loan_lines.filtered(
                        lambda l: ps.date_from <= l.date <= ps.date_to
                    )

                    # If payslip is finalized and deduction rule exists, mark installment lines as paid
                    if ps.state == 'done' and has_deduction_line:
                        for line in filtered_lines:
                            line.paid = not ps.credit_note

                    # Sum amounts for the deduction
                    total_deduction += sum(filtered_lines.mapped('amount'))

                ps.housing_advance_deduction = total_deduction

                # Mark loans as granted if allowance line exists (usually HOADALW code)
                has_allowance_line = bool(ps.line_ids.filtered(lambda x: x.code in ['HOADALW']))
                if ps.state == 'done' and has_allowance_line:
                    for loan in housing_adv:
                        loan.loan_granted = not ps.credit_note
            else:
                # If employee not set, reset both fields
                ps.housing_advance_deduction = 0
                ps.housing_advance_grant = 0

    def action_payslip_paid(self):
        """
        Trigger housing advance computation before marking payslip as paid.
        """
        for rec in self:
            rec._calc_housing_advance()
        return super().action_payslip_paid()

    def compute_sheet(self):
        """
        Trigger housing advance computation before computing the payslip.
        """
        for rec in self:
            rec._calc_housing_advance()
        return super().compute_sheet()
