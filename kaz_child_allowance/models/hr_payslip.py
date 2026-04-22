# -*- coding: utf-8 -*-
"""
Extends hr.payslip to compute and include a 'Child Allowance' component
based on approved child allowance requests within the payslip period.
"""

from odoo import models, fields


class HrPayslip(models.Model):
    """
    Inherits the `hr.payslip` model to introduce child allowance integration.

    Features:
    - Computes a fixed child allowance (e.g., 600 per eligible child) for
      employees marked as 'local'.
    - Checks for approved and unpaid child allowance requests whose date falls
      within the payslip period.
    - Automatically marks allowances as paid when the payslip is paid.
    - Makes the amount available via a computed monetary field for use in
      salary rules or reporting.
    """
    _inherit = 'hr.payslip'

    # Computed amount of child allowance to be used in salary rule computation.
    child_allowance_kaz = fields.Monetary(string="Child Allowance")

    def compute_sheet(self):
        """
        Overrides the default payslip computation to include child allowance
        before calculating other salary rules.
        """
        for rec in self:
            # Update environment context with the current payslip ID
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
            })
            # Compute child allowance based on eligibility
            rec.child_allowance()
        return super().compute_sheet()

    def child_allowance(self):
        """
        Computes the child allowance for the current payslip.

        Eligibility criteria:
        - Employee must be of type 'local'.
        - Child allowance request must be approved.
        - Request date should be within the payslip period.
        - Request should not have been already marked as paid.

        Marks the child allowance record as paid if the context contains `paid`.

        Returns:
            float: Total child allowance calculated.
        """
        payslip_id = self.env.context.get('allowance_payslip_id')
        allowance_amt = 0.0
        payslip = self.env['hr.payslip'].browse(payslip_id)
        contract = payslip.contract_id
        employee = contract.employee_id

        if employee.kaz_employee_type == 'local':
            allowances = self.env['child.allowance'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'approved'),
                ('date', '>=', payslip.date_from),
                ('date', '<=', payslip.date_to),
                ('paid', '=', False),
            ])

            for allowance in allowances:
                for kid in allowance.kid_ids:
                    if kid.is_eligible:
                        allowance_amt += 600  # Fixed amount per child

                # Mark as paid if the payslip is being processed as paid
                if (
                        self.env.context.get('paid') and
                        payslip.line_ids.filtered(lambda x: x.code == 'CHLALW')
                ):
                    allowance.write({'paid': True})

        self.child_allowance_kaz = allowance_amt
        return allowance_amt

    def action_payslip_paid(self):
        """
        When the payslip is marked as paid, this method ensures that
        corresponding child allowance records are also marked as paid.
        """
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
                'paid': True,
            })
            rec.child_allowance()
        return super().action_payslip_paid()
