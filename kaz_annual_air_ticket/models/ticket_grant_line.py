# -*- coding: utf-8 -*-
from odoo import fields, models


class TicketGrantLines(models.Model):
    """
    Model: ticket.grant.line
    Description:
        Represents an individual employee’s air ticket entry under a ticket grant batch.

    Fields:
        - employee_id (Many2one): Employee receiving the ticket.
        - destination_id (Many2one): Destination from employee profile.
        - no_adults / no_children / no_infant: Passenger counts from employee profile.
        - ticket_type_id (Many2one): Type of ticket from employee’s grade.
        - total_air_tickets (Float): Computed ticket cost.
        - paid (Boolean): Marks if the ticket is already paid.
    """
    _name = 'ticket.grant.line'
    _description = 'Ticket Grant Line'

    ticket_grant_id = fields.Many2one('ticket.grant')
    employee_id = fields.Many2one('hr.employee', string='Employee Name')
    grade_id = fields.Many2one('hr.grade', related='employee_id.grade_id')
    destination_id = fields.Many2one(string='Destination', related='employee_id.destination_id',
                                     store=True, readonly=False)
    no_adults = fields.Integer(string='No of Adults', related='employee_id.adults', store=True,
                               readonly=False)
    no_children = fields.Integer(string='No of Children', related='employee_id.children',
                                 store=True, readonly=False)
    no_infant = fields.Integer(string='No of Infant', related='employee_id.infant', store=True,
                               readonly=False)
    ticket_type_id = fields.Many2one(string='Ticket Type', related='grade_id.ticket_type_id',
                                     store=True)
    total_air_tickets = fields.Float()
    paid = fields.Boolean(string="Paid", copy=False)
    ticket_grant_state = fields.Selection(related='ticket_grant_id.state')

    def _compute_emp_total_ticket_price(self):
        """
        Compute total ticket price for the employee based on:
            - Matching price list within the grant date range
            - Employee's ticket type and destination
            - Number of adults/children/infants
        Returns:
            float: Total calculated price
        """
        for rec in self:
            tickets = self.env['price.list.ticket'].search([
                ('ticket_type_id', '=', rec.employee_id.ticket_type_id.id)
            ]).filtered(lambda x: x.start_date <= rec.ticket_grant_id.date <= x.end_date)

            ticket = tickets[0] if tickets else None
            if ticket:
                price_lines = ticket.ticket_lines_ids.filtered(
                    lambda l: l.destination_id.id == rec.destination_id.id
                )
                price_line = price_lines[0] if price_lines else None

                if price_line:
                    adults = price_line.adults * rec.no_adults
                    children = price_line.children * rec.no_children
                    infant = price_line.infant * rec.no_infant
                    total_price = adults + children + infant
                    return total_price

        return 0.0  # Fallback
