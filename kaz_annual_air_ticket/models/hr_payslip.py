# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """
    Extends the hr.payslip model to support:
    - Ticket total price computation for Leave Travel Allowance (LTA)
    - Housing advance grant and deduction (disabled currently via comment)

    Fields:
        ticket_total_price (float): Computed total ticket value for employee, used in LTA rule.
        education_fees (float): Placeholder for education fees (not used in logic yet).
        housing_advance_grant (float): Amount granted as housing advance (disabled currently).
        housing_advance_deduction (float): Deduction due to housing advance (disabled currently).
    """

    _inherit = 'hr.payslip'

    ticket_total_price = fields.Float(string='Ticket Total Price')
    education_fees = fields.Float(string='Education Fees')
    housing_advance_grant = fields.Float(string="Housing advance grant")
    housing_advance_deduction = fields.Float(string="Housing advance Deduction")

    def _calc_ticket_total_price(self):
        """
                Computes the ticket total price for an employee during a payslip period.
                - For 'local' employees: total = current wage
                - For 'expat' employees: total = sum of air ticket costs
                - Marks corresponding ticket lines as paid
                """
        for rec in self:
            tickets = self.env['ticket.grant'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('state', '=', 'confirmed'),
            ])
            if tickets:
                tot = 0
                for t in tickets:
                    if t.ticket_grant_line_ids.filtered(
                            lambda l: l.employee_id == rec.employee_id and not l.paid) and rec.employee_id.kaz_employee_type == 'local':
                        for m in t.ticket_grant_line_ids.filtered(
                                lambda l: l.employee_id == rec.employee_id and not l.paid and l.employee_id.kaz_employee_type == 'local'):
                            m.paid = True
                        tot = rec.contract_id.wage
                    elif t.ticket_grant_line_ids.filtered(
                            lambda l: l.employee_id == rec.employee_id and not l.paid) and rec.employee_id.kaz_employee_type == 'expat':
                        for x in t.ticket_grant_line_ids.filtered(
                                lambda l: l.employee_id == rec.employee_id and not l.paid and l.employee_id.kaz_employee_type == 'expat'):
                            x.paid = True
                        tot += sum(t.ticket_grant_line_ids.filtered(
                            lambda
                                l: l.employee_id == rec.employee_id and not l.paid and l.employee_id.kaz_employee_type == 'expat').mapped(
                            'total_air_tickets'))
                rec.ticket_total_price = tot
            else:
                rec.ticket_total_price = 0

    def compute_sheet(self):
        """
                Overrides payslip compute to:
                - Calculate ticket total price before standard computation
                """
        for rec in self:
            # rec._calc_housing_advance()
            rec._calc_ticket_total_price()
        return super().compute_sheet()
