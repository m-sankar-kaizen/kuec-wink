# -*- coding: utf-8 -*-
from odoo import models, fields

class HrPayslip(models.Model):
    """
    Inherits the `hr.payslip` model to compute a dynamic living allowance
    based on the employee's spouse's grade. Overrides the `compute_sheet` method
    to inject context and recalculate `living_allowance` before computing the sheet.
    """
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        """
        Overrides the core payroll sheet computation method.

        Adds the current payslip ID to the context using `allowance_payslip_id`.
        Then updates the linked contract’s `living_allowance` field by calling
        `living_allowance()` which applies business logic based on spouse eligibility.

        Returns:
            res (bool): Result of the standard payslip computation (super call).
        """
        for rec in self:
            # Duplicate and update the environment context for this payslip record
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
            })

            # Calculate and set dynamic living allowance based on spouse grade
            rec.contract_id.living_allowance = rec.living_allowance()

        # Proceed with normal payslip computation
        return super().compute_sheet()

    def living_allowance(self):
        """
        Custom method to calculate the living allowance for the employee
        taking into consideration the spouse’s grade if applicable.

        Business Rules:
            - If the employee has a spouse who is also an employee:
                - If the employee’s grade has a higher or equal living allowance
                  than the spouse’s grade → use full employee value.
                - Otherwise, apply a 20% reduction to the employee’s living allowance.
            - If no spouse exists → use the full employee’s grade living allowance.

        Returns:
            float: Calculated monthly living allowance value for payroll use.
        """
        # Fetch payslip ID from context (injected in compute_sheet)
        payslip_id = self.env.context.get('allowance_payslip_id')

        # Retrieve the current payslip and linked contract
        payslip = self.env['hr.payslip'].browse(payslip_id)
        contract = payslip.contract_id

        # Check for a spouse who is also an employee
        spouse_id = contract.employee_id.spouse_employee_id

        if spouse_id:
            # Retrieve both spouse and employee grade living allowances
            spouse_grade = spouse_id.grade_id
            spouse_living_allowance = spouse_grade.monthly_living_allowance
            employee_living_allowance = contract.employee_id.grade_id.monthly_living_allowance

            # Apply reduction rule if employee's allowance is less than spouse's
            if employee_living_allowance >= spouse_living_allowance:
                living_allowance = employee_living_allowance
            else:
                living_allowance = employee_living_allowance * 0.80  # 20% reduction
        else:
            # No spouse, use full employee living allowance
            living_allowance = contract.employee_id.grade_id.monthly_living_allowance

        return living_allowance
