# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AnnualTicket(models.Model):
    """
    Model: price.list.ticket
    Description:
        Manages annual ticket pricing for different ticket types within a specific date range.
        Used for computing leave travel allowance (LTA) or similar ticket benefits for employees.

    Fields:
        name (Char): Sequence-based unique identifier for the ticket price list.
        start_date (Date): Start date of the ticket pricing validity.
        end_date (Date): End date of the ticket pricing validity.
        ticket_type_id (Many2one): Reference to the ticket type (e.g., Local, Expat).
        ticket_lines_ids (One2many): Related ticket line records defining per-destination rates.
        state (Selection): Workflow state of the record (Draft, Confirmed, Cancelled).

    Behavior:
        - Auto-generates sequence on creation.
        - Supports state transitions: draft, confirm, cancel.
    """
    _name = 'price.list.ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Annual Ticket'

    name = fields.Char(default=lambda x: _('New'))
    start_date = fields.Date(
        string='Start Date',
        tracking=True)
    end_date = fields.Date(
        string='End Date',
        tracking=True)
    ticket_type_id = fields.Many2one(
        'ticket.type',
        string='Type',
        tracking=True,
        required=True)
    ticket_lines_ids = fields.One2many(
        'price.list.ticket.lines',
        'ticket_id',
        string='Annual Ticket Lines',
        tracking=True)
    state = fields.Selection(
        string='State',
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancelled')
        ],
        default='draft',
        tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to assign a sequence to the name field
        if it is not explicitly provided.
        """
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ticket.seq') or _('New')
        return super().create(vals_list)

    def action_draft(self):
        """
        Set the record state back to 'draft'.
        """
        self.state = 'draft'

    def action_cancel(self):
        """
        Set the record state to 'cancel'.
        """
        self.state = 'cancel'

    def action_confirm(self):
        """
        Set the record state to 'confirm'.
        """
        self.state = 'confirm'
