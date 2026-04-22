# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class AnnualTicketType(models.Model):
    """
    Model: ticket.type
    Description:
        Defines the different types of air tickets (e.g., economy, business, etc.)
        that can be used in the annual ticketing system. This model is used
        in price lists and linked to employee grades.

    Inherits:
        - mail.thread: For chatter tracking
        - mail.activity.mixin: For activities

    Fields:
        - name (Char): Name/label for the ticket type.
    """
    _name = 'ticket.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Ticket Type'

    name = fields.Char(tracking=True)

    def unlink(self):
        """
        Prevent deletion of a ticket type if it is used in any
        price list record (`price.list.ticket`).

        Raises:
            ValidationError: If the ticket type is linked to any price list.
        """
        for rec in self:
            check_type = self.env['price.list.ticket'].search([
                ('ticket_type_id', '=', rec.id)
            ])
            if check_type:
                raise ValidationError(_("This ticket type is already in use and cannot be deleted."))
        return super().unlink()
