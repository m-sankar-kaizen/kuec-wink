# -*- coding: utf-8 -*-
from odoo import models, fields


class HrGrade(models.Model):
    """
    Inherits hr.grade to define travel ticket type eligibility for each employee grade.

    This allows assigning a specific ticket type (e.g., Economy, Business) to
    employees based on their grade level, which can be used in travel-related
    modules like annual ticket requests or acting allowance.
    """
    _inherit = 'hr.grade'

    ticket_type_id = fields.Many2one(
        'ticket.type',
        string='Ticket Type',
        help="Defines the travel ticket type assigned to this grade (e.g., Economy, Business)."
    )
