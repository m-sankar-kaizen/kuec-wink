# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    """
    Extension of hr.employee model to include travel-related information.

    Fields:
        - destination_id: Preferred travel destination for the employee.
        - adults: Number of adult dependents for ticket allocation.
        - children: Number of child dependents for ticket allocation.
        - infant: Number of infant dependents for ticket allocation.
        - ticket_type_id: Type of ticket eligible based on grade.
        - attachment: Optional document (e.g., passport, ticket copy).
    """
    _inherit = 'hr.employee'

    destination_id = fields.Many2one(
        'res.destination',
        string='Destination',
        help="Preferred travel destination for this employee."
    )
    adults = fields.Integer(
        string='Adults',
        help="Number of adult dependents eligible for tickets."
    )
    children = fields.Integer(
        string='Children',
        help="Number of children eligible for tickets."
    )
    infant = fields.Integer(
        string='Infant',
        help="Number of infants eligible for tickets."
    )
    ticket_type_id = fields.Many2one(
        'ticket.type',
        string='Type',
        related="grade_id.ticket_type_id",
        store=True,
        readonly=True,
        help="Type of ticket based on employee grade."
    )
    attachment = fields.Binary(
        string="Attachment",
        groups='hr.group_hr_user',
        help="Attach any relevant document such as travel approval, passport, etc."
    )
