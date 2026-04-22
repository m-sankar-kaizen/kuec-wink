# -*- coding: utf-8 -*-
"""
Extends the hr.payslip model to handle acting allowance logic:
- Computes acting allowance dynamically for eligible employees.
- Deducts acting allowance based on validated leave days (threshold-based).
"""
from odoo import models
from dateutil.relativedelta import relativedelta


class HrPayslip(models.Model):
    """
     Inherits the hr.payslip model to integrate acting allowance handling.

     This extension enables:
     - Automatic calculation of acting allowance based on conditions.
     - Deduction of acting allowance when leave thresholds are crossed.
     - Context-aware computation to update the contract dynamically.
     """
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        """
        Override compute_sheet to update the acting allowance amount
        on the contract before payroll computation.
        """
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
            })
            rec.contract_id.acting_allowance_amount = rec.acting_allowance()
        return super().compute_sheet()

    def acting_allowance(self):
        """
        Calculate acting allowance amount for the current payslip based on:
        - Employee grade eligibility.
        - State of the acting allowance.
        - Whether current payslip is within or after the first 3 months.

        :return: Computed allowance amount (float)
        """
        payslip = self.env['hr.payslip'].browse(
            self.env.context.get('allowance_payslip_id'))
        contract = payslip.contract_id
        acting_allowance = contract.acting_allowance_id
        acting_allowance_amount = 0.0

        if contract.grade_id.is_allow_acting_allowance:
            if acting_allowance.state == 'approved' and payslip.date_from > acting_allowance.from_date + relativedelta(
                    months=3):
                delta = relativedelta(payslip.date_from,
                                      acting_allowance.from_date)
                months_diff = delta.months + (delta.years * 12)

                if (delta.days == 0 and months_diff == 4) or (
                        delta.days > 0 and months_diff == 3):
                    acting_allowance_amount = acting_allowance.acting_allowance_amount * 3
                else:
                    acting_allowance_amount = acting_allowance.acting_allowance_amount
        return acting_allowance_amount

    def acting_allowance_deduction(self):
        """
        Compute deduction from acting allowance if validated leaves exceed 7 days per month.

        Deduction logic:
        - For the 4th month payslip (after 3 months of acting period), split leaves into 3 months and calculate deductions.
        - For other months, calculate total validated leaves and deduct if >= 7 days.

        :return: Total deducted amount (float)
        """
        payslip = self.env['hr.payslip'].browse(
            self.env.context.get('allowance_payslip_id'))
        contract = payslip.contract_id
        acting_allowance = contract.acting_allowance_id
        acting_allowance_amt = acting_allowance.acting_allowance_amount
        amount_per_day = acting_allowance_amt / 30.0
        deducted_amt = 0.0

        if contract.grade_id.is_allow_acting_allowance and acting_allowance.state == 'approved' \
                and payslip.date_from > acting_allowance.from_date + relativedelta(
            months=3):

            delta = relativedelta(payslip.date_from, acting_allowance.from_date)
            months_diff = delta.months + (delta.years * 12)

            validated_leaves = self.env['hr.leave'].search(
                [('state', '=', 'validate')])

            if (delta.days == 0 and months_diff == 4) or (
                    delta.days > 0 and months_diff == 3):
                # Compute for 3 months individually
                periods = []
                start = acting_allowance.from_date
                for _ in range(3):
                    end = start + relativedelta(months=1)
                    periods.append((start, end))
                    start = end

                month_leave_days = [0, 0, 0]  # days for month 1, 2, 3

                for leave in validated_leaves:
                    leave_start = leave.date_from.date()
                    leave_end = leave.date_to.date()
                    for i, (start, end) in enumerate(periods):
                        days = self._compute_overlap_days(start, end,
                                                          leave_start,
                                                          leave_end)
                        month_leave_days[i] += days

                for days in month_leave_days:
                    if days >= 7:
                        deducted_amt += days * amount_per_day

            else:
                # Standard month deduction
                leave_days = 0
                for leave in validated_leaves:
                    leave_start = leave.date_from.date()
                    leave_end = leave.date_to.date()
                    leave_days += self._compute_overlap_days(payslip.date_from,
                                                             payslip.date_to,
                                                             leave_start,
                                                             leave_end)

                if leave_days >= 7:
                    deducted_amt += leave_days * amount_per_day

        return deducted_amt

    def _compute_overlap_days(self, period_start, period_end, leave_start,
                              leave_end):
        """
        Utility method to compute overlapping days between leave and a given period.

        :param period_start: Start date of the period
        :param period_end: End date of the period
        :param leave_start: Start date of the leave
        :param leave_end: End date of the leave
        :return: Number of overlapping days (int)
        """
        start = max(period_start, leave_start)
        end = min(period_end, leave_end)
        delta = (end - start).days
        return max(delta, 0)
