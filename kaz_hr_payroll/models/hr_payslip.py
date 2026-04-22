# -*- coding: utf-8 -*-
"""
    Module: hr_holidays_custom (or hr_payroll_custom if separated)

    This model extends the `hr.payslip` model to include post-payment integration
    with the ticket grant system.

    When a payslip is marked as paid, this override checks for air ticket
    grants that:
        - Are within the date range of the payslip
        - Are in 'confirmed' state
        - Belong to the same employee

    It then marks the related `ticket.grant.line` entries as paid.

    Author: Midhun
    Date: July 2025
"""
from odoo import models


class HrPayroll(models.Model):
    """
    Inherits:
        hr.payslip (Odoo core model)

    Purpose:
        Extends the standard payroll process by automatically marking related
        air ticket grant lines as paid when the payslip is marked paid.

    Assumptions:
    ------------
    - A custom model `ticket.grant` exists which includes:
        - A date field (`date`)
        - A one2many field `ticket_grant_line_ids` linking to individual employees
        - A state field (`state`) with a value `confirmed`
    - The `ticket.grant.line` model has:
        - Fields: `employee_id`, `paid` (Boolean)

    Methods:
        - action_payslip_paid(): Overrides the default behavior to integrate with ticket payments.
    """

    _inherit = 'hr.payslip'

    def action_payslip_paid(self):
        """
        Overrides the standard method `action_payslip_paid` to:
        1. Call the super method to mark the payslip as paid.
        2. Search for `ticket.grant` records within the payslip period
           that are in 'confirmed' state.
        3. For each matching grant, loop through its lines and mark as paid
           if the line belongs to the employee in the payslip and is unpaid.

        Returns:
            res (any): Result from the super method.
        """
        res = super().action_payslip_paid()
        for rec in self:
            # Search for ticket grants in the date range of the payslip
            tickets = self.env['ticket.grant'].search([
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('state', '=', 'confirmed'),
            ])

            if tickets:
                for t in tickets:
                    # Mark only the unpaid ticket lines for this employee
                    unpaid_lines = t.ticket_grant_line_ids.filtered(
                        lambda l: l.employee_id == rec.employee_id and not l.paid
                    )
                    unpaid_lines.paid = True  # Set paid = True for each applicable line

        return res
