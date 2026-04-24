# -*- coding: utf-8 -*-
from odoo import fields, models, Command


class TicketGrant(models.Model):
    """
    Model: ticket.grant
    Description:
        Represents the granting of annual air tickets to employees.
        Each record corresponds to a batch of ticket grants, typically run for a particular date.

    Fields:
        - state (Selection): Workflow state - Draft, Confirmed, or Cancelled.
        - date (Date): Effective date of ticket granting.
        - ticket_grant_line_ids (One2many): Lines with per-employee ticket data.
    """
    _name = 'ticket.grant'
    _description = 'Ticket Grant'
    _rec_name = 'date'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancel')
    ], default='draft')
    date = fields.Date(string='Date', required=True)
    ticket_grant_line_ids = fields.One2many('ticket.grant.line', 'ticket_grant_id')

    def btn_confirm(self):
        """Transition the ticket grant to the 'confirmed' state."""
        self.state = 'confirmed'

    def btn_cancel(self):
        """Transition the ticket grant to the 'cancel' state."""
        self.state = 'cancel'

    def get_employees(self):
        """
        Fetch eligible employees for annual air ticket grant based on:
            - Active open contract with 'annual_air_ticket' = True
            - Joined at least one year ago
        Clears any existing ticket lines and regenerates them.
        """
        emp_ids = self.env['hr.employee'].search([])
        today = fields.Date.today()
        available_emps_ids = []

        for emp in emp_ids:
            running_contract = self.env['hr.contract'].search([
                ('employee_id', '=', emp.id),
                ('annual_air_ticket', '=', True),
                ('state', '=', 'open'),
            ]).filtered(lambda c: c.date_start <= today and (not c.date_end or c.date_end >= today))

            if running_contract and emp.hire_date and (today - emp.hire_date).days >= 365:
                available_emps_ids.append(emp.id)

        # Clear existing lines
        self.ticket_grant_line_ids.unlink()

        # Create new lines
        self.write({
            'ticket_grant_line_ids': [Command.create({'employee_id': emp_id}) for emp_id in
                                      available_emps_ids]
        })

    def calculate_amount(self):
        """
        Calculates the ticket price per employee line
        using `_compute_emp_total_ticket_price` and updates the field.
        """
        for rec in self:
            for line in rec.ticket_grant_line_ids:
                line.total_air_tickets = line._compute_emp_total_ticket_price()
