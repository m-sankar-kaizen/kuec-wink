# -*- coding: utf-8 -*-
from odoo import models, fields


class Destination(models.Model):
    """
    Destination Model

    This model is used to define destinations which can be used in workflows like
    travel management, ticketing systems, or location-specific benefits.

    Fields:
        - name (Char): Name of the destination (e.g., "Dubai").
        - code (Char): Short code or identifier for the destination (e.g., "DXB").
    """
    _name = 'res.destination'
    _description = 'Destination'

    name = fields.Char(
        string="Destination Name",
        required=True,
        help="The full name of the destination, e.g., 'Dubai'."
    )

    code = fields.Char(
        string="Code",
        required=True,
        help="A short code to identify the destination, e.g., 'DXB'."
    )
