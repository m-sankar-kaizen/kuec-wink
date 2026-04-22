# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeePublic(models.Model):
    """
    Extension of hr.employee.public to expose limited ticket-related info to general users.

    Fields:
        - destination_id: Public view of the travel destination.
        - adults: Public view of adult count for ticketing.
        - children: Public view of child count for ticketing.
        - infant: Public view of infant count for ticketing.
        - ticket_type_id: Ticket type based on grade, public visibility.
    """
    _inherit = 'hr.employee.public'

    destination_id = fields.Many2one(
        'res.destination',
        string='Destination',
        help="Preferred travel destination for this employee."
    )
    adults = fields.Integer(
        string='Adults',
        help="Number of adult dependents for travel."
    )
    children = fields.Integer(
        string='Children',
        help="Number of children dependents for travel."
    )
    infant = fields.Integer(
        string='Infant',
        help="Number of infant dependents for travel."
    )
    ticket_type_id = fields.Many2one(
        'ticket.type',
        string='Type',
        related="grade_id.ticket_type_id",
        store=True,
        readonly=True,
        help="Type of ticket based on employee grade."
    )
    # attachment = fields.Binary()  # Not exposed on public model
