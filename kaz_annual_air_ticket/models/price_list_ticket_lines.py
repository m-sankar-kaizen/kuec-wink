# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AnnualTicketLines(models.Model):
    """
    Model: price.list.ticket.lines
    Description:
        Represents individual ticket pricing lines under a ticket price list.
        Each line is associated with a destination and defines the cost per passenger type.

    Fields:
        ticket_id (Many2one): Reference to the parent annual ticket price list.
        destination_id (Many2one): The travel destination (e.g., Dubai, Riyadh).
        adults (Float): Cost of the ticket per adult.
        children (Float): Cost of the ticket per child.
        infant (Float): Cost of the ticket per infant.
        id_no (Integer): Sequence number within the ticket lines, auto-computed.
        code (Char): Destination short code, fetched from destination_id.code (related field).

    Behavior:
        - Automatically computes a running sequence number (`id_no`) per ticket_id for display.
    """
    _name = 'price.list.ticket.lines'
    _description = 'Ticket Lines'

    ticket_id = fields.Many2one('price.list.ticket', string='Annual Ticket')
    destination_id = fields.Many2one('res.destination', string='Destination')
    adults = fields.Float(string='Adults')
    children = fields.Float(string='Children')
    infant = fields.Float(string='Infant')
    id_no = fields.Integer(string='ID', readonly=True, compute='_compute_counter')
    code = fields.Char(related='destination_id.code')

    @api.depends('ticket_id', 'id_no')
    def _compute_counter(self):
        """
        Compute a line number (id_no) for each line in the ticket,
        used for reference or reporting purposes.
        The sequence is recomputed every time a line is added or removed.
        """
        for ticket in self.mapped('ticket_id'):
            number = 1
            for line in ticket.ticket_lines_ids:
                line.id_no = number
                number += 1
