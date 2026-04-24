# -*- coding: utf-8 -*-
from odoo import models, fields


class HrContract(models.Model):
    """
    Extension of the 'hr.contract' model to support housing advance deduction tracking.

    This model adds a computed monetary field `housing_advance_deduction` that dynamically calculates
    the total deduction applicable for the employee based on approved housing advance loans within
    the current month. It aggregates all loan line entries under approved and granted housing loans.

    Key Features:
    - Computes monthly housing advance deduction amount
    - Only considers loans with state 'approve' and 'loan_granted' as True
    - Filters loan lines by current calendar month for deduction relevance
    """
    _inherit = 'hr.contract'

    housing_advance_deduction = fields.Monetary(
        string="Housing Advance Deduction",
        compute='compute_housing_advance'
    )

    def compute_housing_advance(self):
        """
        Compute the total housing advance deduction for the current month.

        For each contract, if the associated employee has one or more approved and granted
        housing loans, the method sums up all loan line amounts from those loans that fall
        within the current calendar month. The result is stored in the field
        `housing_advance_deduction`.

        If no employee is set or no matching loans exist, the deduction is set to 0.0.
        """
        for rec in self:
            if rec.employee_id:
                # Fetch all approved and granted housing loans for the employee
                housing_advs = self.env['hr.loan'].sudo().search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'approve'),
                    ('loan_granted', '=', True),
                ])
                total_deduction = 0.0
                for housing_adv in housing_advs:
                    # Filter loan lines belonging to the current calendar month
                    filtered_lines = housing_adv.sudo().loan_lines.filtered(
                        lambda line: fields.Date.today().month == line.date.month
                    )
                    # Sum the amounts of the filtered loan lines
                    total_deduction += sum(filtered_lines.mapped('amount'))
                rec.housing_advance_deduction = total_deduction
            else:
                rec.housing_advance_deduction = 0.0
